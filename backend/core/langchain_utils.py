from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage, HumanMessage
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.chains import LLMChain

from core.config import settings

def get_llm(temperature=0.2):
    """Initialize a Gemini LLM with specified temperature"""
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature,
        convert_system_message_to_human=True
    )

def create_prompt_template(system_template, human_template):
    """Create a ChatPromptTemplate with system and human messages"""
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
    return ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

def create_chain(llm, prompt_template):
    """Create a simple LLMChain with the given LLM and prompt template"""
    return LLMChain(llm=llm, prompt=prompt_template)

# Parsing helpers
def create_pydantic_parser(pydantic_object):
    """Create a PydanticOutputParser for the specified Pydantic model"""
    return PydanticOutputParser(pydantic_object=pydantic_object)

# Constants for system messages
RAG_SYSTEM_TEMPLATE = """You are a specialized NVIDIA financial report analysis agent. Your task is to provide accurate information from NVIDIA's quarterly reports based on the user's query.
Use only the provided context to answer. If you don't have enough information in the context, acknowledge the limitations of your data.
Focus on extracting factual information and insights from the reports without adding your own opinions."""

SNOWFLAKE_SYSTEM_TEMPLATE = """You are a specialized financial analyst focused on NVIDIA's valuation metrics. Your task is to provide insights and analysis based on structured financial data from Snowflake.
Provide data-driven analysis of NVIDIA's valuation metrics over time, identifying trends and making comparisons. Include clear explanations of what these metrics mean for the company's financial health."""

WEB_SEARCH_SYSTEM_TEMPLATE = """You are a specialized web research agent focused on NVIDIA. Your task is to provide real-time insights and market analysis based on web search results.
Analyze the search results to identify relevant trends, news, and market sentiment about NVIDIA. Focus on providing up-to-date information that complements historical financial data."""

REPORT_SYSTEM_TEMPLATE = """You are a comprehensive NVIDIA research assistant that combines historical report analysis, structured financial data, and real-time web insights.
Your task is to generate a well-structured research report that provides a holistic view of NVIDIA's performance and market position.
Organize the report into clear sections: Historical Performance, Financial Metrics, and Real-time Market Insights."""