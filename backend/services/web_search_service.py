import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.core.config import settings

logger = logging.getLogger(__name__)

class WebSearchService:
    def __init__(self):
        """Initialize the web search service using SerpAPI"""
        self.api_key = settings.SERPAPI_API_KEY
        self.base_url = "https://serpapi.com/search"
        
    def search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform a web search using SerpAPI
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            List of search results with title, snippet, and link
        """
        # Append NVIDIA to the query if not already present
        if "nvidia" not in query.lower():
            query = f"NVIDIA {query}"
            
        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "num": num_results,
                "tbm": "nws"  # News search
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract and format results
            results = []
            if "news_results" in data:
                for item in data["news_results"]:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "link": item.get("link", ""),
                        "source": item.get("source", ""),
                        "date": item.get("date", "")
                    })
            elif "organic_results" in data:
                for item in data["organic_results"]:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "link": item.get("link", ""),
                        "source": item.get("source", "") if "source" in item else "",
                        "date": item.get("date", "") if "date" in item else ""
                    })
                    
            return results
            
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return []
            
    def search_financial_news(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Specialized search for financial news about NVIDIA"""
        financial_query = f"NVIDIA {query} financial earnings stock"
        return self.search(financial_query, num_results)
        
    def search_product_news(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Specialized search for NVIDIA product news"""
        product_query = f"NVIDIA {query} new products technology GPU AI"
        return self.search(product_query, num_results)
    
    def get_trending_topics(self) -> List[Dict[str, Any]]:
        """Get current trending topics related to NVIDIA"""
        return self.search("NVIDIA trending news", 5)