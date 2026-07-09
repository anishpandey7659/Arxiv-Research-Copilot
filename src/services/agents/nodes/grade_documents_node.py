import logging
import time
from typing import Dict

import logfire

from langgraph.runtime import Runtime

from ..context import Context
from ..models import GradingResult,GradeDocuments
from ..prompts import GRADE_DOCUMENTS_PROMPT
from ..state import AgentState
from .utils import extract_sources_from_tool_messages, get_latest_context, get_latest_query

logger = logging.getLogger(__name__)


@logfire.instrument("node:grade_documents", extract_args=False)
async def ainvoke_grade_documents_step(
    state: AgentState,
    runtime: Runtime[Context],
) -> Dict[str, str | list]:
    """Grade retrieved documents for relevance using LLM.

    This function uses an LLM to evaluate whether the retrieved documents
    are relevant to the user's query and decides whether to generate an
    answer or rewrite the query for better results.

    :param state: Current agent state
    :param runtime: Runtime context
    :returns: Dictionary with routing_decision and grading_results
    """
    logfire.info("NODE: grade_documents")
    start_time = time.time()

    # Get query and context
    question = get_latest_query(state["messages"])
    context = get_latest_context(state["messages"])

    # Extract document chunks from context for logging
    chunks_preview = []
    if context:
        # Context is a string containing all documents concatenated
        # Let's show a preview of what was retrieved
        context_preview = context[:500] + "..." if len(context) > 500 else context
        chunks_preview = [{"text_preview": context_preview, "length": len(context)}]

    # Create span for document grading
    span = None
    if runtime.context.langfuse_enabled and runtime.context.trace:
        try:
            span = runtime.context.langfuse_tracer.create_span(
                trace=runtime.context.trace,
                name="document_grading",
                input_data={
                    "query": question,
                    "context_length": len(context) if context else 0,
                    "has_context": context is not None,
                    "chunks_received": chunks_preview,
                },
                metadata={
                    "node": "grade_documents",
                    "model": runtime.context.model_name,
                },
            )
            logfire.debug("Created Langfuse span for document grading")
        except Exception as e:
            logfire.warning(f"Failed to create span for grade_documents node: {e}")

    if not context:
        logfire.warning("No context found, routing to rewrite_query")

        # Update span with no context result
        if span:
            execution_time = (time.time() - start_time) * 1000
            runtime.context.langfuse_tracer.end_span(
                span,
                output={"routing_decision": "rewrite_query", "reason": "no_context"},
                metadata={"execution_time_ms": execution_time},
            )

        return {"routing_decision": "rewrite_query", "grading_results": []}

    logfire.debug(f"Grading context of length {len(context)} characters")

    # Use LLM to grade document relevance (plain text — avoids structured output failures on small models)
    try:
        grading_prompt = GRADE_DOCUMENTS_PROMPT.format(
            context=context,
            question=question,
        )

        logfire.info("Invoking LLM for document grading ")
        grade_result = await runtime.context.llm_client.get_structured_response(
            query=grading_prompt,
            system_prompt="",
            schema_model=GradeDocuments,
            model_group='structured-output',
        )

        if grade_result is None:
            raise ValueError("LLM returned None for grading result")
        
        if grade_result.binary_score == 'yes':
            is_relevant = True
        if grade_result.binary_score == 'no':
            is_relevant = False

        logfire.info(f"LLM grading result: is_relevant={is_relevant}, response_snippet={grade_result.reasoning}")

        grading_result = GradingResult(
            document_id="retrieved_docs",
            is_relevant=is_relevant,
            reasoning=grade_result.reasoning,
        )

    except Exception as e:
        logfire.error(f"LLM grading failed: {e}, failing open")
        # Fail open: if we retrieved any context, attempt to generate an answer
        is_relevant = bool(context.strip())
        grading_result = GradingResult(
            document_id="retrieved_docs",
            is_relevant=is_relevant,
            reasoning=f"Fallback (LLM error): {'proceeding with context' if is_relevant else 'no context available'}",
        )

    # Determine routing
    route = "generate_answer" if is_relevant else "rewrite_query"

    logfire.info(f"Grading result: {'relevant' if is_relevant else 'not relevant'}, routing to: {route}")

    # Update span with grading result
    if span:
        execution_time = (time.time() - start_time) * 1000
        runtime.context.langfuse_tracer.end_span(
            span,
            output={
                "routing_decision": route,
                "is_relevant": is_relevant,
                "reasoning": grading_result.reasoning,
            },
            metadata={
                "execution_time_ms": execution_time,
                "context_length": len(context),
            },
        )

    relevant_sources = extract_sources_from_tool_messages(state["messages"]) if is_relevant else []

    return {
        "routing_decision": route,
        "grading_results": [grading_result],
        "relevant_sources": relevant_sources,
    }
