import logging
from typing import Dict, Any, List, Optional

from langchain.schema import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from core.langchain_utils import get_llm, create_prompt_template, WEB_SEARCH_SYSTEM_TEMPLATE
from core.models import TimeRange, AgentResponse, AgentType
from services.web_search_service import WebSearchService

logger = logging.getLogger(__name__)

class WebSearchAgent:
    def __init__(self):
        """Initialize the Web Search agent with web search service"""
        self.web_search_service = WebSearchService()
        self.llm = get_llm(temperature=0.3)  # Slightly higher temperature for more diverse responses
        
    async def process_query(self, query: str, time_range: Optional[TimeRange] = None) -> AgentResponse:
        """
        Process a query using web search
        
        Args:
            query: The user query
            time_range: Optional time range filter (not directly used for web search)
            
        Returns:
            Agent response with content and metadata
        """
        try:
            # Perform web search
            search_results = self.web_search_service.search(query, num_results=7)
            
            if not search_results:
                return AgentResponse(
                    agent_type=AgentType.WEB_SEARCH,
                    content="I couldn't find any relevant information about NVIDIA from web search. Please try a different query."
                )
            
            # Also get financial news and trending topics
            financial_news = self.web_search_service.search_financial_news(query, num_results=3)
            trending_topics = self.web_search_service.get_trending_topics()
            
            # Format search results
            search_text = self._format_search_results(search_results)
            financial_text = self._format_search_results(financial_news, "Financial News")
            trending_text = self._format_search_results(trending_topics, "Trending NVIDIA Topics")
            
            # Combine all results
            combined_text = f"{search_text}\n\n{financial_text}\n\n{trending_text}"
            
            # Create prompt
            human_template = """
            Based on web search results about NVIDIA, please answer the following question:

            Question: {query}

            Here are the relevant web search results:
            {search_results}

            Please provide a comprehensive analysis based on these real-time web results.
            Focus on current market trends, news, and insights about NVIDIA that complement historical financial data.
            """
            
            prompt = create_prompt_template(
                system_template=WEB_SEARCH_SYSTEM_TEMPLATE,
                human_template=human_template
            )
            
            # Generate response
            response = await self.llm.ainvoke(
                prompt.format_messages(
                    query=query,
                    search_results=combined_text
                )
            )
            
            # Extract sources
            sources = [result.get("source", "") for result in search_results if "source" in result]
            
            return AgentResponse(
                agent_type=AgentType.WEB_SEARCH,
                content=response.content,
                data={
                    "sources": sources,
                    "result_count": len(search_results) + len(financial_news) + len(trending_topics)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in Web Search agent: {e}")
            return AgentResponse(
                agent_type=AgentType.WEB_SEARCH,
                content=f"I encountered an error while searching for NVIDIA information: {str(e)}"
            )
    
    def _format_search_results(self, results: List[Dict[str, Any]], section_title: str = "General Search Results") -> str:
        """Format search results into a readable string"""
        if not results:
            return f"{section_title}:\nNo results found."
            
        formatted_results = [f"{section_title}:"]
        
        for i, result in enumerate(results):
            result_text = f"Result {i+1}:\n"
            result_text += f"Title: {result.get('title', 'N/A')}\n"
            result_text += f"Source: {result.get('source', 'N/A')}\n"
            result_text += f"Date: {result.get('date', 'N/A')}\n"
            result_text += f"Snippet: {result.get('snippet', 'N/A')}\n"
            
            formatted_results.append(result_text)
        
        return "\n\n".join(formatted_results)