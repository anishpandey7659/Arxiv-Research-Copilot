from src.services.opensearch.factory import make_opensearch_client_fresh
from src.services.LLM_gateway.factory import make_groq_llm_client
from src.services.guardrails.Input_guardrails.factory import make_Input_guardrails
from src.services.embeddings.factory import make_embeddings_service
from src.services.langfuse.factory import make_langfuse_tracer
import  asyncio
from src.services.agents.agentic_rag import AgenticRAGService

rag=AgenticRAGService(
                    make_opensearch_client_fresh(host="http://localhost:9200"),
                    make_embeddings_service(),
                    make_groq_llm_client(),
                    make_Input_guardrails(),
                    make_langfuse_tracer()
                    )


async def main():
    query="Fuck you"
    user_id ='user_1'
    model="openai/gpt-oss-120b"

    result = await rag.ask(query,user_id,model)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())