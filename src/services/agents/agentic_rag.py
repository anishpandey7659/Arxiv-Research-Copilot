import time
from typing import List,Optional
from .nodes import ( ainvoke_generate_answer_step,ainvoke_grade_documents_step,continue_after_guardrail,
                    ainvoke_guardrail_step,ainvoke_out_of_scope_step,ainvoke_retrieve_step,
                    ainvoke_rewrite_query_step
    
                    )
from langgraph.graph import END, StateGraph, START
from langchain.messages import HumanMessage
from langgraph.prebuilt import ToolNode, tools_condition
from .context import Context
from.state import AgentState
from src.services.langfuse.client import LangfuseTracer
from.tools import create_retriever_tool
from src.services.opensearch.client import OpenSearchClient
from src.services.embeddings.jina_client import EmbeddingsClient
from.config import GraphConfig
from src.services.llm_gateway.client import LLMClient
from src.services.guardrails.Input_guardrails.client import InputGuardrails


import logging
logger = logging.getLogger(__name__)

class AgenticRAGService:
    
    def __init__(self,opensearch:OpenSearchClient,embeddings_client:EmbeddingsClient,
                 llm_client:LLMClient,guardrails:InputGuardrails,langfuse_tracer:LangfuseTracer,graph_config:GraphConfig):
        self.opensearch = opensearch
        self.embeddings_client =embeddings_client
        self.llm_client= llm_client
        self.guardrails= guardrails
        
        self.config=graph_config
        self.langfuse_tracer =langfuse_tracer
        # build graph
        self.graph =self.build_graph()
    
    def build_graph(self):
        logger.info(f"Intializing langgraph workflow")
        
        retriever_tool =create_retriever_tool(opensearch_client=self.opensearch,
                                    embeddings_client=self.embeddings_client,
                                    top_k=self.config.top_k,
                                    use_hybrid=True)
        tools = [retriever_tool]

        # Create workflow with AgentState and Context schema
        workflow = StateGraph(AgentState, context_schema=Context)
        
        logger.info("Adding Node on Graph")
        
        workflow.add_node("input_guardrail",ainvoke_guardrail_step)
        workflow.add_node("out_of_scope",ainvoke_out_of_scope_step)
        workflow.add_node("retrive_step",ainvoke_retrieve_step)
        workflow.add_node("grade_documents",ainvoke_grade_documents_step)
        workflow.add_node("rewrite_query",ainvoke_rewrite_query_step)
        workflow.add_node("generate_answer",ainvoke_generate_answer_step)
        workflow.add_node("tool_retrive",ToolNode(tools))

        workflow.add_edge(START,"input_guardrail")
        # Guardrail → route based on score
        workflow.add_conditional_edges(
            'input_guardrail',
            continue_after_guardrail,
            {
                'out_of_scope':"out_of_scope",
                'continue':'retrive_step'
            }
        )
        workflow.add_edge('out_of_scope',END)
        workflow.add_conditional_edges(
            'retrive_step',
            tools_condition,
            {
                "tools":"tool_retrive",
                END:END
            }
        )
        workflow.add_edge("tool_retrive","grade_documents")
        # After grading → route based on relevance
        workflow.add_conditional_edges(
            "grade_documents",
            lambda state: state.get("routing_decision", "generate_answer"),
            {
                "generate_answer": "generate_answer",
                "rewrite_query": "rewrite_query",
            },
        )
        workflow.add_edge("generate_answer",END)
        workflow.add_edge("rewrite_query","retrive_step")
        
        # Compile graph
        logger.info("Compiling LangGraph workflow")

        graph= workflow.compile()
        return graph

    async def ask(
        self,
        query: str,
        user_id: str = "api_user",
        model: Optional[str] = None,
    ) -> dict:
        """Ask a question using agentic RAG.

        :param query: User question
        :param user_id: User identifier for tracing
        :param model: Optional model override
        :returns: Dictionary with answer, sources, reasoning steps, and metadata
        :raises ValueError: If query is empty
        """
        model_to_use = model or self.config.model

        # Validate input
        if not query or len(query.strip()) == 0:
            logger.error("Empty query received")
            raise ValueError("Query cannot be empty")

        # Create trace if Langfuse is enabled (v3 SDK)
        trace = None
        if self.langfuse_tracer and self.langfuse_tracer.client:
            logger.info("Creating Langfuse trace (v3 SDK)")
            metadata = {
                "env": self.config.settings.environment,
                "service": "agentic_rag",
                "top_k": self.config.top_k,
                "use_hybrid": self.config.use_hybrid,
                "model": model_to_use,
            }
            trace = self.langfuse_tracer.client.start_as_current_observation(
                name="agentic_rag_request",
                as_type="span",
            )

        # Use proper context manager pattern
        async def _execute_with_trace():
            """Execute the workflow with or without tracing context."""
            if trace is not None:
                with trace as trace_obj:
                    trace_obj.update(
                        input={"query": query},
                        metadata=metadata,
                        user_id=user_id,
                        session_id=f"session_{user_id}",
                    )
                    logger.debug(f"Trace created: {trace_obj}")
                    return await self._run_workflow(query,user_id,trace_obj)
            else:
                return await self._run_workflow(query, user_id,trace=None)

        try:
            return await _execute_with_trace()
        except Exception as e:
            logger.error(f"Error in Agentic RAG execution: {str(e)}")
            logger.exception("Full traceback:")
            raise


    async def _run_workflow(self,query:str,user_id:str,trace):
        try:
            start_time = time.time()
            trace_id = self.langfuse_tracer.get_trace_id() if self.langfuse_tracer else None
            
            logger.info("Invoking LangGraph workflow")

            state_input = {
                    "messages":[HumanMessage(content=query)],
                    "retrieval_attempts":0,
                    "guardrail_result":None,
                    "classifier_output":None,
                    "routing_decision":None,
                    "sources":None,
                    "relevant_sources":None,
                    "metadata":None
            }
            runtime_context =Context(
                llm_client= self.llm_client,
                opensearch_client= self.opensearch,
                embeddings_client= self.embeddings_client,
                langfuse_tracer =self.langfuse_tracer,
                guardrails_service =self.guardrails,
                trace=trace,
                langfuse_enabled=self.langfuse_tracer is not None and self.langfuse_tracer.client is not None,
                temperature =self.config.temperature,
                top_k=self.config.top_k,
                max_retrieval_attempts=self.config.max_retrieval_attempts
            )

            config = {"thread_id": f"user_{user_id}_session_{int(time.time())}"}
            
            if self.langfuse_tracer is not None and trace:
                try:
                    from langfuse.langchain import CallbackHandler
                    callback_handler = CallbackHandler() 
                    config["callbacks"] = [callback_handler]  
                    logger.info("✓ CallbackHandler added (will auto-link to current trace)")
                
                except Exception as e:
                    logger.error(f'Got Error while creating callback handler: {e}')
            
            result = await self.graph.ainvoke(
                state_input,
                config=config,
                context=runtime_context,
            )
            execution_time = time.time() - start_time
            logger.info(f"✓ Graph execution completed in {execution_time:.2f}s")
            
            answer=self._extract_answer(result)
            sources = self._extract_sources(result)
            retrieval_attempts = result.get("retrieval_attempts", 0)
            reasoning_steps=self._extract_reasoning(result)
            model = result.get('model')
            if trace:
                trace.update(
                    output={
                        "answer": answer,
                        "sources_count": len(sources),
                        "retrieval_attempts": retrieval_attempts,
                        "reasoning_steps": reasoning_steps,
                        "execution_time": execution_time,
                    }
                )
                trace.end()
                self.langfuse_tracer.flush()

            return {
                "question":query,
                "answer":answer,
                "user_id":user_id,
                "model_use":model,
                "Sources":sources,
                "resoning":reasoning_steps,
                "retrieval_attempts":retrieval_attempts,
                "execution_time":execution_time,
                "trace_id":trace_id
            }
        
        except Exception as e:
            logger.error(f"Error in workflow execution: {str(e)}")
            logger.exception("Full traceback:")

            # Update trace with error (cleanup handled by context manager)
            if trace:
                trace.update(output={"error": str(e)}, level="ERROR")
                trace.end()
                self.langfuse_tracer.flush()

            raise

    
    def _extract_sources(self,result: dict)->List[dict]:
        """Extract sources from graph result."""
        sources = []
        relevant_sources = result.get("relevant_sources", [])

        if relevant_sources:
            for source in relevant_sources:
                if hasattr(source, "to_dict"):
                    sources.append(source.to_dict())
                elif isinstance(source, dict):
                    sources.append(source)

            return sources
        return []

    def _extract_answer(self,result:dict)->str:
        message = result.get('messages','')
        if not message:
            return "No answer generated"
        final_message = message[-1].content
        return final_message.content if hasattr(final_message, "content") else str(final_message)

    def _extract_reasoning(self,result:dict)->List:
        steps=[]
        document_grade = result.get('grading_results',[])
        guardrails_result = result.get('guardrail_result')
        retrieval_attempt=result.get('retrieval_attempts',0)
        rewritten_query=result.get("rewritten_query")

        if guardrails_result:
            steps.append(f"Guardrails category into: {guardrails_result.category} , reason: {guardrails_result.reason} ")

        if retrieval_attempt>0:
            steps.append(f"Retrived document: {retrieval_attempt} attempts")
        
        if rewritten_query:
            steps.append(f"Rewrite the user query: {rewritten_query}")

        if document_grade:
            reasons = "; ".join(doc.reasoning for doc in document_grade)
            steps.append(f"We chose these docs cause: {reasons}")

        return steps


    def get_graph_visualization(self) -> bytes:
        """Get the LangGraph workflow visualization as PNG.

        This method generates a visual representation of the graph workflow
        using mermaid diagram format, then converts it to PNG.

        :returns: PNG image bytes
        :raises ImportError: If required dependencies (pygraphviz/graphviz) are not installed
        :raises Exception: If graph visualization generation fails

        Example:
            >>> service = AgenticRAGService(...)
            >>> png_bytes = service.get_graph_visualization()
            >>> with open("graph.png", "wb") as f:
            ...     f.write(png_bytes)
        """
        try:
            logger.info("Generating graph visualization as PNG")
            png_bytes = self.graph.get_graph().draw_mermaid_png()
            logger.info(f"✓ Generated PNG visualization ({len(png_bytes)} bytes)")
            return png_bytes
        except ImportError as e:
            logger.error(f"Failed to generate visualization - missing dependencies: {e}")
            logger.error("Install with: pip install pygraphviz or apt-get install graphviz")
            raise ImportError(
                "Graph visualization requires pygraphviz. "
                "Install with: pip install pygraphviz (requires graphviz system package)"
            ) from e
        except Exception as e:
            logger.error(f"Failed to generate graph visualization: {e}")
            raise

    def get_graph_mermaid(self) -> str:
        """Get the LangGraph workflow as a mermaid diagram string.

        This method generates the graph workflow representation in mermaid
        diagram syntax, which can be rendered in markdown or mermaid viewers.

        :returns: Mermaid diagram syntax as string

        Example:
            >>> service = AgenticRAGService(...)
            >>> mermaid = service.get_graph_mermaid()
            >>> print(mermaid)
            graph TD
                __start__ --> guardrail
                ...
        """
        try:
            logger.info("Generating graph as mermaid diagram")
            mermaid_str = self.graph.get_graph().draw_mermaid()
            logger.info(f"✓ Generated mermaid diagram ({len(mermaid_str)} characters)")
            return mermaid_str
        except Exception as e:
            logger.error(f"Failed to generate mermaid diagram: {e}")
            raise

    def get_graph_ascii(self) -> str:
        """Get ASCII representation of the graph.

        This method generates a simple ASCII art representation of the
        graph structure, useful for quick inspection in terminals.

        :returns: ASCII art representation of the graph

        Example:
            >>> service = AgenticRAGService(...)
            >>> print(service.get_graph_ascii())
        """
        try:
            logger.info("Generating ASCII graph representation")
            ascii_str = self.graph.get_graph().print_ascii()
            logger.info("✓ Generated ASCII graph representation")
            return ascii_str
        except Exception as e:
            logger.error(f"Failed to generate ASCII graph: {e}")
            raise
