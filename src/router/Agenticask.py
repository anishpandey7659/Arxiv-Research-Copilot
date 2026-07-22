from fastapi import APIRouter, HTTPException
from src.dependencies import AgenticRAGDep, LangfuseDep,CacheDep
from src.schemas.api.ask import AgenticAskResponse, AskRequest, FeedbackRequest, FeedbackResponse
import logfire


router = APIRouter(prefix="/api/v1", tags=["agentic-rag"])


import logfire

@router.post("/ask-agentic", response_model=AgenticAskResponse)
async def ask_agentic(
    request: AskRequest,
    agentic_rag: AgenticRAGDep,
    cache: CacheDep
) -> AgenticAskResponse:
    with logfire.span("ask_agentic", query=request.query, user_id=request.user_id):
        try:
            if cache:
                with logfire.span("cache_lookup"):
                    cached_answer = await cache.find_cached_response(request, AgenticAskResponse)
                if cached_answer:
                    logfire.info("cache_hit", query=request.query)
                    return cached_answer

            with logfire.span("agentic_rag_ask") as span:
                result = await agentic_rag.ask(query=request.query)
                span.set_attribute("retrieval_attempts", result.get("retrieval_attempts", 0))
                span.set_attribute("sources_count", len(result.get("sources", [])))

            response = AgenticAskResponse(
                user_id=request.user_id,
                query=request.query,
                answer=result.get("answer") or "No answer generated.",
                sources=result.get("sources", []),
                chunks_used=request.top_k,
                search_mode="hybrid" if request.use_hybrid else "bm25",
                reasoning_steps=result.get("reasoning_steps", []),
                retrieval_attempts=result.get("retrieval_attempts", 0),
                rewritten_query=result.get("rewritten_query"),
                trace_id=result.get("trace_id"),
                guardrail_filter=result.get("guardrail_filter"),
                model_use=result.get("model_use"),
                execution_time=result.get("execution_time") or 0.0,
            )

            if cache:
                try:
                    await cache.store_response(request, response)
                except Exception as e:
                    logfire.warning("cache_store_failed", error=str(e))

            return response

        except ValueError as e:
            logfire.error("validation_error", error=str(e))
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logfire.exception("ask_agentic_failed")
            raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    langfuse_tracer: LangfuseDep,
) -> FeedbackResponse:
    """
    Submit user feedback for an agentic RAG response.

    This endpoint allows users to rate the quality of answers and provide
    optional comments. Feedback is tracked in Langfuse for continuous improvement.

    Args:
        request: Feedback data including trace_id, score, and optional comment
        langfuse_tracer: Injected Langfuse tracer service

    Returns:
        FeedbackResponse indicating success or failure

    Raises:
        HTTPException: If feedback submission fails
    """
    try:
        if not langfuse_tracer:
            raise HTTPException(
                status_code=503,
                detail="Langfuse tracing is disabled. Cannot submit feedback."
            )

        success = langfuse_tracer.submit_feedback(
            trace_id=request.trace_id,
            score=request.score,
            comment=request.comment,
        )

        if success:
            # Flush to ensure feedback is sent immediately
            langfuse_tracer.flush()

            return FeedbackResponse(
                success=True,
                message="Feedback recorded successfully"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to submit feedback to Langfuse"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting feedback: {str(e)}"
        )