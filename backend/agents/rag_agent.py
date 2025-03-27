import logging
from typing import Dict, Any, List, Optional

from langchain.schema import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from core.langchain_utils import get_llm, create_prompt_template, RAG_SYSTEM_TEMPLATE
from core.models import TimeRange, AgentResponse, AgentType
from services.pinecone_service import PineconeService

logger = logging.getLogger(__name__)

class RAGAgent:
    def __init__(self):
        """Initialize the RAG agent with Pinecone service"""
        self.pinecone_service = PineconeService()
        self.llm = get_llm(temperature=0.2)
        
    async def process_query(self, query: str, time_range: Optional[TimeRange] = None) -> AgentResponse:
        """
        Process a query using RAG with Pinecone
        
        Args:
            query: The user query
            time_range: Optional time range filter
            
        Returns:
            Agent response with content and metadata
        """
        try:
            # Search for relevant documents
            search_results = self.pinecone_service.hybrid_search(
                query=query,
                time_range=time_range,
                top_k=5
            )
            
            if not search_results:
                return AgentResponse(
                    agent_type=AgentType.RAG,
                    content="I couldn't find any relevant information in NVIDIA's quarterly reports for the specified time period. Please try a different query or time range."
                )
            
            # Extract content from search results
            contexts = [f"Document {i+1}:\n{result['content']}\n\nSource: {result['metadata']['quarter_label']} - Page {result['metadata']['page']}" 
                       for i, result in enumerate(search_results)]
            
            # Join contexts with line breaks
            context_text = "\n\n".join(contexts)
            
            # Create prompt
            human_template = """
            Based on NVIDIA's quarterly reports, please answer the following question:

            Question: {query}

            Here is the relevant information from the reports:
            {context}

            Please provide a detailed and factual response based solely on the information provided.
            """
            
            prompt = create_prompt_template(
                system_template=RAG_SYSTEM_TEMPLATE,
                human_template=human_template
            )
            
            # Generate response
            response = await self.llm.ainvoke(
                prompt.format_messages(
                    query=query,
                    context=context_text
                )
            )
            
            # Extract sources for citation
            sources = set()
            for result in search_results:
                if 'metadata' in result and 'quarter_label' in result['metadata']:
                    sources.add(result['metadata']['quarter_label'])
            
            # Sort sources
            sorted_sources = sorted(list(sources))
            
            return AgentResponse(
                agent_type=AgentType.RAG,
                content=response.content,
                data={
                    "sources": sorted_sources,
                    "result_count": len(search_results)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in RAG agent: {e}")
            return AgentResponse(
                agent_type=AgentType.RAG,
                content=f"I encountered an error while searching NVIDIA's quarterly reports: {str(e)}"
            )