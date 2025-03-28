import streamlit as st
import requests
import json
import pandas as pd
import base64
from PIL import Image
import io
from datetime import datetime

# API Configuration
API_URL = "http://127.0.0.1:8000"  # Docker service name

# Set page configuration
st.set_page_config(
    page_title="NVIDIA Research Assistant",
    page_icon="📊",
    layout="wide"
)

# Add custom CSS
st.markdown("""
<style>
    .main {
        padding: 1rem;
    }
    .section-header {
        background-color: #76b900;  /* NVIDIA green */
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .agent-section {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        border-left: 5px solid #76b900;
    }
    /* 新增的样式 */
    .agent-section-rag {
        background-color: rgba(118, 185, 0, 0.1);  /* 淡绿色背景 */
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        border-left: 5px solid #76b900;
    }
    .agent-section-web {
        background-color: rgba(118, 185, 0, 0.1);  /* 淡绿色背景 */
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        border-left: 5px solid #76b900;
    }
    .agent-header-green {
        color: #76b900;  /* NVIDIA绿色文字 */
        font-weight: bold;
    }
    .report-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        border: 1px solid #ddd;
    }
    .stButton>button {
        background-color: #76b900;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def get_available_quarters():
    """Get list of available quarters from the API"""
    try:
        response = requests.get(f"{API_URL}/api/available-quarters")
        data = response.json()
        return data.get("quarters", [])
    except Exception as e:
        st.error(f"Error fetching available quarters: {str(e)}")
        return []

def format_quarter_label(quarter_label):
    """Format quarter label for display (e.g., 2021q1 -> Q1 2021)"""
    year, quarter = quarter_label.split("q")
    return f"Q{quarter} {year}"

def generate_report(start_quarter, end_quarter):
    """Generate comprehensive report"""
    try:
        payload = {
            "time_range": {
                "start_quarter": start_quarter,
                "end_quarter": end_quarter
            }
        }
        
        with st.spinner("Generating comprehensive report... This may take a minute."):
            response = requests.post(
                f"{API_URL}/api/generate-report",
                json=payload
            )
            
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error generating report: {str(e)}")
        return None

def query_agents(query, selected_agents, start_quarter, end_quarter):
    """Query specific agents"""
    try:
        payload = {
            "query": query,
            "agents": selected_agents,
            "time_range": {
                "start_quarter": start_quarter,
                "end_quarter": end_quarter
            }
        }
        
        with st.spinner("Querying agents... This may take a moment."):
            response = requests.post(
                f"{API_URL}/api/agent-query",
                json=payload
            )
            
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error querying agents: {str(e)}")
        return None

def display_chart(base64_str, caption=""):
    """Display a chart from base64 string"""
    if not base64_str:
        return
    
    try:
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))
        st.image(image, caption=caption, use_container_width=True)
    except Exception as e:
        st.error(f"Error displaying chart: {str(e)}")

# Main App
def main():
    # Header
    st.title("🔍 NVIDIA Research Assistant")
    st.markdown("### Comprehensive research using Snowflake, RAG, and Web Search")
    
    # Sidebar for time range selection
    st.sidebar.header("Time Range Selection")
    
    # Get available quarters
    quarters = get_available_quarters()
    if not quarters:
        st.error("Failed to fetch available quarters. Please check if the backend is running.")
        return
    
    # Sort quarters for display
    quarters.sort()
    
    # Format quarters for display in the dropdown
    display_quarters = [format_quarter_label(q) for q in quarters]
    quarter_mapping = dict(zip(display_quarters, quarters))
    
    # Select start and end quarters
    start_display = st.sidebar.selectbox(
        "Start Quarter", 
        options=display_quarters,
        index=0
    )
    
    # Determine valid end quarters (must be >= start quarter)
    start_idx = display_quarters.index(start_display)
    valid_end_options = display_quarters[start_idx:]
    
    end_display = st.sidebar.selectbox(
        "End Quarter", 
        options=valid_end_options,
        index=len(valid_end_options) - 1
    )
    
    # Convert to backend format
    start_quarter = quarter_mapping[start_display]
    end_quarter = quarter_mapping[end_display]
    
    st.sidebar.markdown(f"Selected range: **{start_display}** to **{end_display}**")
    
    # Tab layout
    tabs = st.tabs(["Comprehensive Report", "Custom Query"])
    
    # Tab 1: Comprehensive Report
    with tabs[0]:
        st.header("Comprehensive NVIDIA Research Report")
        st.markdown(f"This report combines data from NVIDIA's quarterly reports, financial metrics, and real-time web insights for the period from **{start_display}** to **{end_display}**.")
        
        # Generate report button
        if st.button("Generate Comprehensive Report", key="gen_report"):
            report = generate_report(start_quarter, end_quarter)
            
            if report:
                # Store report in session state
                st.session_state.report = report
        
        # Display report if available
        if hasattr(st.session_state, "report"):
            report = st.session_state.report
            
            # Historical Performance Section
            st.markdown("<div class='section-header'><h3>📜 Historical Performance</h3></div>", unsafe_allow_html=True)
            st.markdown("<div class='report-section'>", unsafe_allow_html=True)
            st.markdown(report["historical_performance"])
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Financial Metrics Section
            st.markdown("<div class='section-header'><h3>📈 Financial Metrics</h3></div>", unsafe_allow_html=True)
            st.markdown("<div class='report-section'>", unsafe_allow_html=True)
            st.markdown(report["financial_metrics"])
            
            # Charts
            if "charts" in report and report["charts"]:
                st.subheader("Financial Visualization")
                cols = st.columns(len(report["charts"]))
                
                for i, (chart_name, chart_data) in enumerate(report["charts"].items()):
                    with cols[i]:
                        display_chart(chart_data, chart_name.replace("_", " ").title())
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Real-time Insights Section
            st.markdown("<div class='section-header'><h3>🌐 Real-time Market Insights</h3></div>", unsafe_allow_html=True)
            st.markdown("<div class='report-section'>", unsafe_allow_html=True)
            st.markdown(report["real_time_insights"])
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Tab 2: Custom Query
    with tabs[1]:
        st.header("Custom NVIDIA Research Query")
        st.markdown("Ask specific questions about NVIDIA and choose which specialized agents to use.")
        
        # Query input
        query = st.text_input("Your question about NVIDIA", "", key="custom_query")
        
        # Agent selection
        st.subheader("Select Agents to Query")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            use_rag = st.checkbox("RAG Agent (Historical Reports)", value=True)
            st.caption("Analyzes NVIDIA's quarterly reports")
            
        with col2:
            use_snowflake = st.checkbox("Snowflake Agent (Financial Metrics)", value=True)
            st.caption("Analyzes structured financial data")
            
        with col3:
            use_web_search = st.checkbox("Web Search Agent (Real-time Data)", value=True)
            st.caption("Provides current market insights")
        
        # Determine selected agents
        selected_agents = []
        if use_rag:
            selected_agents.append("rag")
        if use_snowflake:
            selected_agents.append("snowflake")
        if use_web_search:
            selected_agents.append("web_search")
            
        # If none selected, use all
        if not selected_agents:
            selected_agents = ["all"]
        
        # Query button
        if st.button("Submit Query", key="submit_query") and query:
            result = query_agents(query, selected_agents, start_quarter, end_quarter)
            
            if result:
                # Store result in session state
                st.session_state.query_result = result
        
        # Display query result if available
        if hasattr(st.session_state, "query_result") and query:
            result = st.session_state.query_result
            
            # Display combined response
            st.subheader("Combined Response")
            st.markdown(result["combined_response"])
            
            # Display individual agent responses
            st.subheader("Individual Agent Responses")
            
            for agent_type, response in result["agent_responses"].items():
                # Skip if no content
                if not response or "content" not in response:
                    continue
                    
                # Format agent name
                agent_name = agent_type.upper()
                css_class = "agent-section"  # 默认样式类
                
                if agent_type == "rag":
                    agent_name = "Historical Reports (RAG)"
                    css_class = "agent-section-rag"  # 使用RAG专用样式
                elif agent_type == "snowflake":
                    agent_name = "Financial Metrics (Snowflake)"
                elif agent_type == "web_search":
                    agent_name = "Real-time Insights (Web Search)"
                    css_class = "agent-section-web"  # 使用Web Search专用样式
                
                # Display agent response with appropriate CSS class
                st.markdown(f"<div class='{css_class}'><h4 class='agent-header-green'>{agent_name}</h4>", unsafe_allow_html=True)
                st.markdown(response["content"])
                
                # Display charts if available
                if "data" in response and "charts" in response["data"]:
                    charts = response["data"]["charts"]
                    if charts:
                        st.subheader("Charts")
                        cols = st.columns(len(charts))
                        
                        for i, (chart_name, chart_data) in enumerate(charts.items()):
                            with cols[i]:
                                display_chart(chart_data, chart_name.replace("_", " ").title())
                
                st.markdown("</div>", unsafe_allow_html=True)
    
    # Sidebar footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About this App")
    st.sidebar.markdown("""
    This research assistant leverages three specialized agents:
    - **RAG Agent**: Analyzes NVIDIA's historical reports
    - **Snowflake Agent**: Provides financial valuation metrics
    - **Web Search Agent**: Gathers real-time insights
    """)
    
    # Display indexing status and control
    st.sidebar.markdown("---")
    st.sidebar.subheader("System Status")
    
    if st.sidebar.button("Check Indexing Status"):
        try:
            response = requests.get(f"{API_URL}/api/indexing-status")
            if response.status_code == 200:
                status = response.json()
                if status.get("is_indexing", False):
                    st.sidebar.warning("Indexing is in progress...")
                else:
                    st.sidebar.success("Indexing is not currently running")
        except Exception as e:
            st.sidebar.error(f"Error checking indexing status: {str(e)}")
    
    if st.sidebar.button("Trigger Report Indexing"):
        try:
            response = requests.post(f"{API_URL}/api/index-reports")
            if response.status_code == 200:
                st.sidebar.success("Indexing started in the background")
        except Exception as e:
            st.sidebar.error(f"Error triggering indexing: {str(e)}")

if __name__ == "__main__":
    main()