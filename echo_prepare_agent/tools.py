from strands import tool
import os
import logging
from datetime import datetime
from tavily import TavilyClient
from bedrock_agentcore.memory import MemoryClient

logger = logging.getLogger(__name__)

MCP_REGION = os.getenv("MCP_REGION")
if not MCP_REGION:
    raise RuntimeError("Missing MCP_REGION environment variable")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise RuntimeError("Missing TAVILY_API_KEY environment variable")


def get_prepare_tools(memory_id: str, memory_client: MemoryClient, actor_id: str, session_id: str):
    """
    Get Echo Prepare utility tools:
    - search_study_resources: Web search for educational content (Tavily API)
    - track_topic_confidence: Save/retrieve student confidence levels (Memory-backed)

    Note: The agent generates practice questions and study notes directly using its LLM,
    guided by its system prompt to use these tools for research and tracking.
    """

    # Initialize Tavily client for web search
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

    @tool
    async def search_study_resources(
        query: str,
        top_k: int = 5,
        recency_days: int | None = None
    ) -> dict:
        """
        Search the web for study resources, tutorials, explanations, and educational content.
        Perfect for researching topics, finding practice problems, or discovering learning materials.

        Args:
            query: The search query (e.g., "Python recursion tutorial", "Civil War causes")
            top_k: Number of results to return (1-10, default: 5)
            recency_days: Filter by recency - None for all time, or specify days (e.g., 7 for past week)

        Returns:
            Dictionary with search results including titles, URLs, and content snippets

        Example:
            search_study_resources("explain quantum entanglement simply", top_k=3)
        """
        try:
            search_kwargs = {
                "query": query,
                "max_results": max(1, min(top_k, 10)),
                "include_domains": None,
                "exclude_domains": None,
            }

            if recency_days:
                # Tavily expects: 'day', 'week', 'month', 'year'
                if recency_days <= 1:
                    search_kwargs["time_range"] = "day"
                elif recency_days <= 7:
                    search_kwargs["time_range"] = "week"
                elif recency_days <= 30:
                    search_kwargs["time_range"] = "month"
                else:
                    search_kwargs["time_range"] = "year"

            res = tavily_client.search(**search_kwargs)
            results = []
            for item in res.get("results", []):
                results.append(
                    {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "snippet": item.get("content") or item.get("snippet"),
                        "score": item.get("score"),
                    }
                )

            logger.info(f"Found {len(results)} results for query: {query}")
            return {"results": results, "provider": "tavily", "query": query}

        except Exception as e:
            logger.error(f"Error searching for study resources: {e}")
            return {"error": str(e), "results": []}

    @tool
    async def track_topic_confidence(
        topic: str,
        confidence_level: int,
        notes: str = ""
    ) -> dict:
        """
        Track student confidence level and understanding of specific topics.
        Saves progress to memory for tracking learning over time.

        Args:
            topic: The topic being tracked (e.g., "recursion", "photosynthesis")
            confidence_level: Confidence from 1-10 (1=confused, 10=mastered)
            notes: Optional notes about what's confusing or what's been mastered

        Returns:
            Confirmation with status and study suggestions

        Example:
            track_topic_confidence("Python loops", 7, "Understand for loops well, while loops need practice")
        """
        try:
            confidence_level = max(1, min(confidence_level, 10))  # Clamp to 1-10
            timestamp = datetime.utcnow().isoformat()

            # Determine status and suggestions
            if confidence_level >= 8:
                status = "Mastered"
                suggestion = f"Great work on {topic}! Keep reviewing occasionally to maintain mastery."
            elif confidence_level >= 6:
                status = "Comfortable"
                suggestion = f"You're doing well with {topic}. Practice a few more problems to solidify understanding."
            elif confidence_level >= 4:
                status = "Learning"
                suggestion = f"Keep studying {topic}. Try different resources or practice problems."
            else:
                status = "Needs Work"
                suggestion = f"{topic} needs more attention. Consider watching tutorials or asking for help."

            # Save to memory for progress tracking
            memory_content = f"Topic: {topic} | Confidence: {confidence_level}/10 | Status: {status}"
            if notes:
                memory_content += f" | Notes: {notes}"

            try:
                await memory_client.save_to_memory(
                    memory_id=memory_id,
                    actor_id=actor_id,
                    session_id=session_id,
                    content=memory_content,
                    namespace=f"/confidence-tracking/{actor_id}"
                )
                logger.info(f"Saved confidence tracking to memory: {topic} = {confidence_level}/10")
            except Exception as mem_err:
                logger.warning(f"Failed to save to memory: {mem_err}")

            result = {
                "topic": topic,
                "confidence_level": confidence_level,
                "status": status,
                "notes": notes,
                "suggestion": suggestion,
                "timestamp": timestamp,
                "saved_to_memory": True
            }

            logger.info(f"Tracked confidence for {topic}: {confidence_level}/10 ({status})")
            return result

        except Exception as e:
            logger.error(f"Error tracking topic confidence: {e}", exc_info=True)
            return {"error": str(e)}

    # Return utility tools
    return [
        search_study_resources,
        track_topic_confidence,
    ]
