import logging
from typing import Dict, Any, List, Optional
import json

from langchain.schema import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from core.langchain_utils import get_llm, create_prompt_template, SNOWFLAKE_SYSTEM_TEMPLATE
from core.models import TimeRange, AgentResponse, AgentType
from services.snowflake_service import SnowflakeService

logger = logging.getLogger(__name__)

class SnowflakeAgent:
    def __init__(self):
        """Initialize the Snowflake agent with Snowflake service"""
        self.snowflake_service = SnowflakeService()
        self.llm = get_llm(temperature=0.2)
        
    async def process_query(self, query: str, time_range: TimeRange) -> AgentResponse:
        """
        Process a query using Snowflake data
        
        Args:
            query: The user query
            time_range: Time range for data retrieval
            
        Returns:
            Agent response with content and metadata
        """
        try:
            # Get valuation metrics for the specified time range
            metrics = self.snowflake_service.get_valuation_metrics(time_range)
            
            if not metrics:
                return AgentResponse(
                    agent_type=AgentType.SNOWFLAKE,
                    content="I couldn't find any valuation metrics for NVIDIA in the specified time period. Please try a different time range."
                )
            
            # Convert metrics to a more readable format
            metrics_text = self._format_metrics_for_prompt(metrics)
            
            # Generate charts
            charts = self.snowflake_service.generate_metrics_charts(time_range)
            
            # Create prompt
            human_template = """
            Based on NVIDIA's valuation metrics, please answer the following question:

            Question: {query}

            Here are the relevant valuation metrics:
            {metrics}

            Please provide a detailed and data-driven analysis based solely on these metrics.
            Explain what these metrics indicate about NVIDIA's financial health and market position.
            Include explanations of the metrics for better understanding.
            """
            
            prompt = create_prompt_template(
                system_template=SNOWFLAKE_SYSTEM_TEMPLATE,
                human_template=human_template
            )
            
            # Generate response
            response = await self.llm.ainvoke(
                prompt.format_messages(
                    query=query,
                    metrics=metrics_text
                )
            )
            
            return AgentResponse(
                agent_type=AgentType.SNOWFLAKE,
                content=response.content,
                data={
                    "charts": charts,
                    "metrics_count": len(metrics),
                    "time_range": {
                        "start": time_range.start_quarter,
                        "end": time_range.end_quarter
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error in Snowflake agent: {e}")
            return AgentResponse(
                agent_type=AgentType.SNOWFLAKE,
                content=f"I encountered an error while analyzing NVIDIA's valuation metrics: {str(e)}"
            )
    
    def _format_metrics_for_prompt(self, metrics: List[Any]) -> str:
        """Format metrics into a readable string for the prompt"""
        formatted_metrics = []
        
        for metric in metrics:
            formatted_metric = f"Quarter: {metric.quarter_label}\n"
            formatted_metric += f"  Market Cap: ${metric.market_cap/1e9:.2f} billion\n"
            formatted_metric += f"  Enterprise Value: ${metric.enterprise_value/1e9:.2f} billion\n"
            formatted_metric += f"  Trailing P/E: {metric.trailing_pe:.2f}\n"
            formatted_metric += f"  Forward P/E: {metric.forward_pe:.2f}\n"
            formatted_metric += f"  Price-to-Sales: {metric.price_to_sales:.2f}\n"
            formatted_metric += f"  Price-to-Book: {metric.price_to_book:.2f}\n"
            formatted_metric += f"  Enterprise-to-Revenue: {metric.enterprise_to_revenue:.2f}\n"
            formatted_metric += f"  Enterprise-to-EBITDA: {metric.enterprise_to_ebitda:.2f}\n"
            
            formatted_metrics.append(formatted_metric)
        
        return "\n".join(formatted_metrics)