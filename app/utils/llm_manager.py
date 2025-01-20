import os 

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_nvidia_ai_endpoints import ChatNVIDIA


from dotenv import load_dotenv
load_dotenv()

class Prompts:
    grid_page_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant that extracts the Product grid page specific links from given set of links.Remember the Product grid links will be unique, they will take the user directly to the products page when clicked.If there are no Links output Empty list",
        ),
        ("human", "Here are the list of Links: {input}"),
    ]
    )
    product_page_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant that extracts the Product specific links from given set of links.Remember the Product links will be unique and long,may contain some product id, they will take the user directly to the product when clicked.If there are no Links output Empty list",
        ),
        ("human", "Here are the list of Links: {input}"),
    ]
    )

def get_llm():
    if os.getenv("SET_OPENAI_MODELS")=="True":
        llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL"),temperature=0,api_key= os.getenv("OPENAI_API_KEY"))
        return llm
    elif os.getenv("SET_OLLAMA")=="True":
        llm = ChatOllama(model=os.getenv("OLLAMA_MODEL"),temperature=0,base_url= os.getenv("OLLAMA_BASE_URL"))
        return llm
    elif os.getenv("SET_NVIDIA")=="True":
        llm = ChatNVIDIA(model=os.getenv("NIM_MODEL"),temperature=0,api_key= os.getenv("NIM_API_KEY"))
        return llm
    
