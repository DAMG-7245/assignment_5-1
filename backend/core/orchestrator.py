import logging
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from langchain_core.output_parsers import StrOutputParser
import asyncio

from langgraph.graph import StateGraph, END


from core.models import TimeRange, AgentRequest, AgentResponse, ReportRequest, ReportResponse, AgentType
from core.langchain_utils import get_llm, create_prompt_template, REPORT_SYSTEM_TEMPLATE
from agents.rag_agent import RAGAgent
from agents.snowflake_agent import SnowflakeAgent
from agents.web_search_agent import WebSearchAgent

logger = logging.getLogger(__name__)

class ResearchOrchestrator:
    def __init__(self):
        """Initialize the research orchestrator with all agents"""
        self.rag_agent = RAGAgent()
        self.snowflake_agent = SnowflakeAgent()
        self.web_search_agent = WebSearchAgent()
        self.llm = get_llm(temperature=0.2)
        
        # Initialize the graph
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph for orchestrating the agents"""
        # Define the state schema
        class AgentState:
            """Schema for the agent state"""
            def __init__(
                self,
                query: str,
                agents: List[AgentType],
                time_range: TimeRange,
                agent_responses: Dict[str, Optional[AgentResponse]] = None,
                combined_response: Optional[str] = None,
                error: Optional[str] = None
            ):
                self.query = query
                self.agents = agents
                self.time_range = time_range
                self.agent_responses = agent_responses or {}
                self.combined_response = combined_response
                self.error = error
        
        # Create the graph with the defined state
        workflow = StateGraph(AgentState)
        
        # Define nodes for each agent
        workflow.add_node("rag_agent", self._run_rag_agent)
        workflow.add_node("snowflake_agent", self._run_snowflake_agent)
        workflow.add_node("web_search_agent", self._run_web_search_agent)
        workflow.add_node("combiner", self._combine_responses)
        
        # Define conditional edges to determine which agents to run
        workflow.add_conditional_edges(
            "root",
            self._route_agents,
            {
                "rag": "rag_agent",
                "snowflake": "snowflake_agent",
                "web_search": "web_search_agent",
                "all": "rag_agent"
            }
        )
        
        # Define edges from agents to combiner or next agent
        workflow.add_conditional_edges(
            "rag_agent",
            self._check_next_agent,
            {
                "snowflake": "snowflake_agent",
                "web_search": "web_search_agent",
                "done": "combiner"
            }
        )
        
        workflow.add_conditional_edges(
            "snowflake_agent",
            self._check_next_agent,
            {
                "web_search": "web_search_agent",
                "done": "combiner"
            }
        )
        
        # Web search always goes to combiner next
        workflow.add_edge("web_search_agent", "combiner")
        
        # Combiner is the final node
        workflow.add_edge("combiner", END)
        
        # Compile the graph
        return workflow.compile()
    
    async def process_agent_request(self, request: AgentRequest) -> Dict[str, Any]:
        """
        Process a request using specific agents
        
        Args:
            request: Agent request with query, agents, and time range
            
        Returns:
            Dictionary with agent responses and combined response
        """
        try:
            # Initialize the state
            state = {
                "query": request.query,
                "agents": [agent.value for agent in request.agents],
                "time_range": request.time_range,
                "agent_responses": {},
                "combined_response": None,
                "error": None
            }
            
            # Execute the graph
            result = await self.graph.ainvoke(state)
            
            # Format the response
            response_dict = {
                "query": request.query,
                "time_range": {
                    "start": request.time_range.start_quarter,
                    "end": request.time_range.end_quarter
                },
                "agent_responses": {
                    agent_type: response.dict() 
                    for agent_type, response in result["agent_responses"].items()
                },
                "combined_response": result["combined_response"]
            }
            
            return response_dict
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            return {
                "error": str(e),
                "query": request.query,
                "time_range": {
                    "start": request.time_range.start_quarter,
                    "end": request.time_range.end_quarter
                }
            }
    
    async def generate_comprehensive_report(self, request: ReportRequest) -> ReportResponse:
        """
        Generate a comprehensive research report
        
        Args:
            request: Report request with time range
            
        Returns:
            Comprehensive report with sections for historical, financial, and real-time data
        """
        try:
            # Create an internal request with all agents
            agent_request = AgentRequest(
                query="Generate a comprehensive research report on NVIDIA for the specified time period",
                agents=[AgentType.RAG, AgentType.SNOWFLAKE, AgentType.WEB_SEARCH],
                time_range=request.time_range
            )
            
            # Process the request
            result = await self.process_agent_request(agent_request)
            
            # Extract agent responses
            rag_response = result["agent_responses"].get("rag", {"content": "No historical data available"})
            snowflake_response = result["agent_responses"].get("snowflake", {"content": "No financial data available"})
            web_search_response = result["agent_responses"].get("web_search", {"content": "No real-time data available"})
            
            # Get charts from Snowflake response
            charts = {}
            if "data" in snowflake_response and "charts" in snowflake_response["data"]:
                charts = snowflake_response["data"]["charts"]
            
            # Create the report
            return ReportResponse(
                historical_performance=rag_response["content"],
                financial_metrics=snowflake_response["content"],
                real_time_insights=web_search_response["content"],
                charts=charts
            )
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return ReportResponse(
                historical_performance=f"Error: {str(e)}",
                financial_metrics="",
                real_time_insights=""
            )
    
    def _route_agents(self, state: Dict[str, Any]) -> str:
        """Determine which agent to run first based on the requested agents"""
        agents = state.get("agents", [])
        
        if AgentType.ALL.value in agents:
            return "all"
        
        if AgentType.RAG.value in agents:
            return "rag"
        
        if AgentType.SNOWFLAKE.value in agents:
            return "snowflake"
        
        if AgentType.WEB_SEARCH.value in agents:
            return "web_search"
        
        # Default to all if no specific agents are requested
        return "all"
    
    def _check_next_agent(self, state: Dict[str, Any]) -> str:
        """Determine which agent to run next based on the requested agents and what's already run"""
        agents = state.get("agents", [])
        agent_responses = state.get("agent_responses", {})
        
        # If "all" is requested, run all agents in sequence
        if AgentType.ALL.value in agents:
            if "rag" in agent_responses and "snowflake" not in agent_responses:
                return "snowflake"
            elif "rag" in agent_responses and "snowflake" in agent_responses:
                return "web_search"
        
        # For specific agent requests, check which ones are left to run
        if AgentType.SNOWFLAKE.value in agents and "snowflake" not in agent_responses:
            return "snowflake"
        
        if AgentType.WEB_SEARCH.value in agents and "web_search" not in agent_responses:
            return "web_search"
        
        # All requested agents have been run
        return "done"
    
    async def _run_rag_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the RAG agent"""
        try:
            query = state.get("query", "")
            time_range = state.get("time_range")
            
            response = await self.rag_agent.process_query(query, time_range)
            
            state["agent_responses"]["rag"] = response
            return state
            
        except Exception as e:
            logger.error(f"Error in RAG agent: {e}")
            state["error"] = f"RAG agent error: {str(e)}"
            return state
    
    async def _run_snowflake_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Snowflake agent"""
        try:
            query = state.get("query", "")
            time_range = state.get("time_range")
            
            response = await self.snowflake_agent.process_query(query, time_range)
            
            state["agent_responses"]["snowflake"] = response
            return state
            
        except Exception as e:
            logger.error(f"Error in Snowflake agent: {e}")
            state["error"] = f"Snowflake agent error: {str(e)}"
            return state
    
    async def _run_web_search_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Web Search agent"""
        try:
            query = state.get("query", "")
            time_range = state.get("time_range")
            
            response = await self.web_search_agent.process_query(query, time_range)
            
            state["agent_responses"]["web_search"] = response
            return state
            
        except Exception as e:
            logger.error(f"Error in Web Search agent: {e}")
            state["error"] = f"Web Search agent error: {str(e)}"
            return state
    
    async def _combine_responses(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Combine responses from all agents"""
        try:
            query = state.get("query", "")
            agent_responses = state.get("agent_responses", {})
            
            if not agent_responses:
                state["combined_response"] = "No responses from any agents."
                return state
            
            # Format input for the combiner
            inputs = []
            
            if "rag" in agent_responses:
                inputs.append(f"Historical Performance (RAG Agent):\n{agent_responses['rag'].content}")
                
            if "snowflake" in agent_responses:
                inputs.append(f"Financial Metrics (Snowflake Agent):\n{agent_responses['snowflake'].content}")
                
            if "web_search" in agent_responses:
                inputs.append(f"Real-time Insights (Web Search Agent):\n{agent_responses['web_search'].content}")
            
            combined_input = "\n\n".join(inputs)
            
            # Create prompt
            human_template = """
            Based on the following agent responses, please provide a consolidated answer to the user's query:

            User Query: {query}

            Agent Responses:
            {combined_input}

            Please synthesize these responses into a coherent and comprehensive answer.
            """
            
            prompt = create_prompt_template(
                system_template=REPORT_SYSTEM_TEMPLATE,
                human_template=human_template
            )
            
            # Generate response
            response = await self.llm.ainvoke(
                prompt.format_messages(
                    query=query,
                    combined_input=combined_input
                )
            )
            
            state["combined_response"] = response.content
            return state
            
        except Exception as e:
            logger.error(f"Error combining responses: {e}")
            state["error"] = f"Error combining responses: {str(e)}"
            state["combined_response"] = "Error combining agent responses."
            return state