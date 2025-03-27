import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional

from core.config import settings
from core.models import (
    TimeRange, 
    AgentType, 
    AgentRequest, 
    AgentResponse, 
    ReportRequest, 
    ReportResponse
)
from core.orchestrator import ResearchOrchestrator
from services.pinecone_service import PineconeService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NVIDIA Research Assistant API",
    description="An integrated research assistant for NVIDIA utilizing Snowflake, RAG, and Web Search",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the orchestrator
orchestrator = ResearchOrchestrator()

# Initialize services for setup
pinecone_service = PineconeService()

# Global flag to track indexing status
is_indexing = False

@app.get("/")
async def root():
    """Root endpoint to check if the API is running"""
    return {"message": "NVIDIA Research Assistant API is running"}

@app.post("/api/agent-query", response_model=Dict[str, Any])
async def agent_query(request: AgentRequest):
    """
    Query specific agents for information about NVIDIA
    
    Args:
        request: Agent request with query, agents, and time range
        
    Returns:
        Dictionary with agent responses and combined response
    """
    try:
        logger.info(f"Received agent query: {request}")
        
        # Process the request
        result = await orchestrator.process_agent_request(request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing agent query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-report", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """
    Generate a comprehensive research report for NVIDIA
    
    Args:
        request: Report request with time range
        
    Returns:
        Comprehensive report with sections for historical, financial, and real-time data
    """
    try:
        logger.info(f"Received report generation request: {request}")
        
        # Generate the report
        report = await orchestrator.generate_comprehensive_report(request)
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/index-reports")
async def index_reports(background_tasks: BackgroundTasks):
    """
    Index NVIDIA reports into Pinecone (runs in background)
    
    Returns:
        Status message
    """
    global is_indexing
    
    if is_indexing:
        return {"message": "Indexing is already in progress"}
    
    # Set indexing flag
    is_indexing = True
    
    # Add background task
    background_tasks.add_task(run_indexing)
    
    return {"message": "Indexing started in the background"}

@app.get("/api/indexing-status")
async def indexing_status():
    """
    Check the status of report indexing
    
    Returns:
        Dictionary with indexing status
    """
    return {"is_indexing": is_indexing}

async def run_indexing():
    """Run the indexing process in the background"""
    global is_indexing
    
    try:
        logger.info("Starting report indexing")
        pinecone_service.load_and_index_reports()
        logger.info("Report indexing completed successfully")
    except Exception as e:
        logger.error(f"Error indexing reports: {e}")
    finally:
        is_indexing = False

@app.get("/api/available-quarters")
async def available_quarters():
    """
    Get list of available quarters for data selection
    
    Returns:
        List of quarter strings in format YYYYqQ (e.g., 2021q1)
    """
    # This would normally come from the database, but for this example we'll hard-code 5 years of quarters
    quarters = []
    for year in range(2020, 2025):
        for q in range(1, 5):
            quarters.append(f"{year}q{q}")
    
    return {"quarters": quarters}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host=settings.API_HOST, 
        port=settings.API_PORT,
        reload=True
    )