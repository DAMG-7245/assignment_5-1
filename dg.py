from diagrams import Diagram, Cluster, Edge
from diagrams.saas.analytics import Snowflake
from diagrams.onprem.container import Docker
from diagrams.programming.framework import FastAPI, Svelte
from diagrams.generic.storage import Storage
from diagrams.programming.language import Python
from diagrams.elastic.elasticsearch import MachineLearning

with Diagram("Nvidia Research Architecture", show=False, direction="LR"):
    # Data Pipeline Section
    with Cluster("Data Pipeline"):
        nvidia_reports = Storage("NVIDIA Reports")
        pinecone = Storage("Pinecone (Vector DB)")
        yahoo_finance = Python("Yahoo Finance")
        snowflake = Snowflake("Snowflake")

    # Connections: Data Pipeline to Agents
    nvidia_reports >> Edge(label="Chunk & Embed") >> pinecone
    yahoo_finance >> Edge(label="Load Structured Data") >> snowflake

    # LangGraph Agents Section
    with Cluster("Query Processing (LangGraph Agents)"):
        rag_agent = MachineLearning("RAG Agent")
        snowflake_agent = MachineLearning("Snowflake Agent")
        web_agent = MachineLearning("Web Search Agent")

    # Connections: Data Sources to LangGraph Agents
    pinecone >> Edge(label="Retrieve Metadata") >> rag_agent
    snowflake >> Edge(label="Query Metrics") >> snowflake_agent

    # Application Layer Section
    with Cluster("Application Layer"):
        streamlit_ui = Svelte("Streamlit UI")
        fastapi_backend = FastAPI("FastAPI Backend")

    # Connections: User Queries and Report Generation
    streamlit_ui >> Edge(label="Generate Report") >> fastapi_backend
    fastapi_backend >> Edge(label="Orchestrate Agents") >> [rag_agent, snowflake_agent, web_agent]
    fastapi_backend >> Edge(label="Submit Queries") >> streamlit_ui

    # Deployment Section
    with Cluster("Deployment"):
        docker_deployment = Docker("Dockerized Deployment")
        docker_deployment >> Edge(label="Deploy Services") >> [streamlit_ui, fastapi_backend]
