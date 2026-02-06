"""
Tool calling support for AI models
Provides Tavily web search integration
"""

import json
from tavily import TavilyClient
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class ToolManager:
    """Simple tool manager for handling web search"""

    def __init__(self):
        """Initialize with Tavily API"""
        self.tavily_client = TavilyClient(api_key=settings.tavily_api_key)
        logger.info("Tavily client initialized")

    def get_tool_definitions(self):
        """
        Returns tool definitions for OpenAI API
        This tells the model what tools are available
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "tavily_search",
                    "description": "Search the web for current information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "What to search for"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def tavily_search(self, query: str):
        """
        Search the web using Tavily API

        Args:
            query: Search query

        Returns:
            Search results
        """
        try:
            logger.info(f"Searching for: {query}")

            # Call Tavily API
            response = self.tavily_client.search(query=query, max_results=5)

    
            results = {
                "query": query,
                "results": []
            }

            if response and "results" in response:
                for item in response["results"]:
                    results["results"].append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", "")
                    })

                logger.info(f"Found {len(results['results'])} results")

            return results

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return {
                "query": query,
                "error": str(e),
                "results": []
            }

    def process_tool_calls(self, tool_calls):
        """
        Process tool calls from the model

        Args:
            tool_calls: Tool calls from OpenAI response

        Returns:
            List of tool results
        """
        results = []

        for tool_call in tool_calls:
            try:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                logger.info(f"Running tool: {tool_name}")

                # Execute the tool
                if tool_name == "tavily_search":
                    query = arguments.get("query", "")
                    result = self.tavily_search(query)
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}

                # Format for OpenAI
                results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(result)
                })

            except Exception as e:
                logger.error(f"Tool execution failed: {str(e)}")
                results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": json.dumps({"error": str(e)})
                })

        return results



tool_manager = ToolManager()



if __name__ == "__main__":
    print("Testing Tavily Search...")
    query = input("Search query: ")
    result = tool_manager.tavily_search(query)
    print(json.dumps(result, indent=2))
