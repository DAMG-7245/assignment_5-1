import logging
from typing import Dict, Any, List, Optional, Callable, Union, Tuple, TypedDict
from langchain_core.output_parsers import StrOutputParser
import asyncio

from langgraph.graph import StateGraph, END

from core.models import TimeRange, AgentRequest, AgentResponse, ReportRequest, ReportResponse, AgentType
from core.langchain_utils import get_llm, create_prompt_template, REPORT_SYSTEM_TEMPLATE
from agents.rag_agent import RAGAgent
from agents.snowflake_agent import SnowflakeAgent
from agents.web_search_agent import WebSearchAgent

logger = logging.getLogger(__name__)

# 简化为使用纯字典状态
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
        """Build the LangGraph for orchestrating the agents using dict-based approach"""
        # 使用纯字典作为状态
        workflow = StateGraph(Dict)
        
        # 添加所有节点
        workflow.add_node("start", self._start_node)
        workflow.add_node("rag_agent", self._run_rag_agent)
        workflow.add_node("snowflake_agent", self._run_snowflake_agent)
        workflow.add_node("web_search_agent", self._run_web_search_agent)
        workflow.add_node("combiner", self._combine_responses)
        
        # 设置入口点
        workflow.set_entry_point("start")
        
        # 从start节点到第一个代理的条件边
        workflow.add_conditional_edges(
            "start",
            self._route_from_start,
            {
                "rag": "rag_agent",
                "snowflake": "snowflake_agent",
                "web_search": "web_search_agent",
                "end": "combiner"
            }
        )
        
        # 从RAG代理到下一步
        workflow.add_conditional_edges(
            "rag_agent",
            self._route_after_rag,
            {
                "snowflake": "snowflake_agent",
                "web_search": "web_search_agent",
                "end": "combiner"
            }
        )
        
        # 从Snowflake代理到下一步
        workflow.add_conditional_edges(
            "snowflake_agent",
            self._route_after_snowflake,
            {
                "web_search": "web_search_agent",
                "end": "combiner"
            }
        )
        
        # Web Search代理总是到Combiner
        workflow.add_edge("web_search_agent", "combiner")
        
        # Combiner是最终节点
        workflow.add_edge("combiner", END)
        
        # 编译图
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
            # 初始化状态
            initial_state = {
                "query": request.query,
                "agents": [agent.value for agent in request.agents],
                "time_range": request.time_range,
                "agent_responses": {},
                "combined_response": None,
                "error": None
            }
            
            # 执行图
            result = await self.graph.ainvoke(initial_state)
            
            # 格式化响应
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
            import traceback
            logger.error(traceback.format_exc())
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
            rag_response = {}
            snowflake_response = {}
            web_search_response = {}
        
            if "agent_responses" in result:
                agent_responses = result["agent_responses"]
                if "rag" in agent_responses:
                    rag_response = agent_responses["rag"]
                if "snowflake" in agent_responses:
                    snowflake_response = agent_responses["snowflake"]
                if "web_search" in agent_responses:
                    web_search_response = agent_responses["web_search"]
            
            # Get charts from Snowflake response
            charts = {}
            if isinstance(snowflake_response, dict) and "data" in snowflake_response:
                if isinstance(snowflake_response["data"], dict) and "charts" in snowflake_response["data"]:
                    charts = snowflake_response["data"]["charts"]
            
            # Create the report
            return ReportResponse(
                historical_performance=rag_response.get("content", "No historical data available"),
                financial_metrics=snowflake_response.get("content", "No financial data available"),
                real_time_insights=web_search_response.get("content", "No real-time data available"),
                charts=charts
            )
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ReportResponse(
                historical_performance=f"Error: Unable to generate historical performance section. {str(e)}",
                financial_metrics="No financial data available.",
                real_time_insights="No real-time insights available."
            )
    def _start_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """初始化节点，确保必要的状态字段存在"""
        # 确保agent_responses字段存在
        if "agent_responses" not in state:
            state["agent_responses"] = {}
        return state
        
    def _route_from_start(self, state: Dict[str, Any]) -> str:
        """决定从start节点应该路由到哪个代理"""
        agents = state.get("agents", [])
        
        if not agents:
            return "end"
            
        if AgentType.RAG.value in agents:
            return "rag"
            
        if AgentType.SNOWFLAKE.value in agents:
            return "snowflake"
            
        if AgentType.WEB_SEARCH.value in agents:
            return "web_search"
            
        return "end"
    
    def _route_after_rag(self, state: Dict[str, Any]) -> str:
        """在RAG代理后决定下一步"""
        agents = state.get("agents", [])
        
        if AgentType.SNOWFLAKE.value in agents:
            return "snowflake"
            
        if AgentType.WEB_SEARCH.value in agents:
            return "web_search"
            
        return "end"
    
    def _route_after_snowflake(self, state: Dict[str, Any]) -> str:
        """在Snowflake代理后决定下一步"""
        agents = state.get("agents", [])
        
        if AgentType.WEB_SEARCH.value in agents:
            return "web_search"
            
        return "end"
    
    async def _run_rag_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """运行RAG代理"""
        try:
            query = state.get("query", "")
            time_range = state.get("time_range")
            
            # 获取RAG代理的响应
            response = await self.rag_agent.process_query(query, time_range)
            
            # 创建一个新的状态字典
            new_state = state.copy()
            
            # 确保agent_responses存在
            if "agent_responses" not in new_state:
                new_state["agent_responses"] = {}
                
            # 添加RAG代理的响应
            new_state["agent_responses"]["rag"] = response
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error in RAG agent: {e}")
            
            # 创建一个新的状态字典
            new_state = state.copy()
            new_state["error"] = f"RAG agent error: {str(e)}"
            
            return new_state
    
    async def _run_snowflake_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """运行Snowflake代理"""
        try:
            query = state.get("query", "")
            time_range = state.get("time_range")
            
            # 获取Snowflake代理的响应
            response = await self.snowflake_agent.process_query(query, time_range)
            
            # 创建一个新的状态字典
            new_state = state.copy()
            
            # 确保agent_responses存在
            if "agent_responses" not in new_state:
                new_state["agent_responses"] = {}
                
            # 添加Snowflake代理的响应
            new_state["agent_responses"]["snowflake"] = response
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error in Snowflake agent: {e}")
            
            # 创建一个新的状态字典
            new_state = state.copy()
            new_state["error"] = f"Snowflake agent error: {str(e)}"
            
            return new_state
    
    async def _run_web_search_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """运行Web Search代理"""
        try:
            query = state.get("query", "")
            time_range = state.get("time_range")
            
            # 获取Web Search代理的响应
            response = await self.web_search_agent.process_query(query, time_range)
            
            # 创建一个新的状态字典
            new_state = state.copy()
            
            # 确保agent_responses存在
            if "agent_responses" not in new_state:
                new_state["agent_responses"] = {}
                
            # 添加Web Search代理的响应
            new_state["agent_responses"]["web_search"] = response
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error in Web Search agent: {e}")
            
            # 创建一个新的状态字典
            new_state = state.copy()
            new_state["error"] = f"Web Search agent error: {str(e)}"
            
            return new_state
    
    async def _combine_responses(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """整合所有代理的响应"""
        try:
            query = state.get("query", "")
            agent_responses = state.get("agent_responses", {})
            
            if not agent_responses:
                # 创建一个新的状态字典
                new_state = state.copy()
                new_state["combined_response"] = "No responses from any agents."
                return new_state
            
            # 格式化输入
            inputs = []
            
            if "rag" in agent_responses:
                inputs.append(f"Historical Performance (RAG Agent):\n{agent_responses['rag'].content}")
                
            if "snowflake" in agent_responses:
                inputs.append(f"Financial Metrics (Snowflake Agent):\n{agent_responses['snowflake'].content}")
                
            if "web_search" in agent_responses:
                inputs.append(f"Real-time Insights (Web Search Agent):\n{agent_responses['web_search'].content}")
            
            combined_input = "\n\n".join(inputs)
            
            # 创建提示
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
            
            # 生成响应
            response = await self.llm.ainvoke(
                prompt.format_messages(
                    query=query,
                    combined_input=combined_input
                )
            )
            
            # 创建一个新的状态字典
            new_state = state.copy()
            new_state["combined_response"] = response.content
            
            return new_state
            
        except Exception as e:
            logger.error(f"Error combining responses: {e}")
            
            # 创建一个新的状态字典
            new_state = state.copy()
            new_state["error"] = f"Error combining responses: {str(e)}"
            new_state["combined_response"] = "Error combining agent responses."
            
            return new_state