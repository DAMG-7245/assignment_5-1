from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from enum import Enum

class TimeRange(BaseModel):
    start_quarter: str  # Format: YYYYqQ (e.g., 2021q1)
    end_quarter: str    # Format: YYYYqQ (e.g., 2021q4)

class AgentType(str, Enum):
    RAG = "rag"
    SNOWFLAKE = "snowflake"
    WEB_SEARCH = "web_search"
    ALL = "all"

class AgentRequest(BaseModel):
    query: str
    agents: List[AgentType]
    time_range: TimeRange

class AgentResponse(BaseModel):
    agent_type: AgentType
    content: str
    data: Optional[Dict[str, Any]] = None
    
class ReportRequest(BaseModel):
    time_range: TimeRange

class ReportResponse(BaseModel):
    historical_performance: str
    financial_metrics: str
    real_time_insights: str
    charts: Optional[Dict[str, Any]] = None
    
class NvidiaValuationMetric(BaseModel):
    """Model for Snowflake data structure"""
    year: int
    quarter: int
    quarter_label: str  # Format: YYYYqQ (e.g., 2021q1)
    market_cap: float
    enterprise_value: float
    trailing_pe: float
    forward_pe: float
    price_to_sales: float
    price_to_book: float
    enterprise_to_revenue: float
    enterprise_to_ebitda: float

class PineconeMetadata(BaseModel):
    """Model for Pinecone metadata"""
    year: int
    quarter: int
    quarter_label: str  # Format: YYYYqQ (e.g., 2021q1)
    source: str
    page: Optional[int] = None