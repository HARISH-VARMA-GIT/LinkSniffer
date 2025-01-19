import asyncio
import aiohttp
from typing import List, Dict

from url_list import website_urls
from dynamic_scraper_with_href_robust import DynamicScraper

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

from rich import print

class Links(BaseModel):
    product_links: list = Field(description="The list of links containing only the product links")

class GridLinks(BaseModel):
    product_grid_links: list = Field(description="The list of links containing the Products page")

def chunk_list(input_list, chunk_size):
    """Split a list into smaller chunks of a given size."""
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i:i + chunk_size]

# Assuming these are your provided functions
async def get_all_href_links(session: aiohttp.ClientSession, url: str) -> List[str]:
    # Your implementation here
    scraper = DynamicScraper(
        headless=True,
        scroll_pause=2,
        max_retries=3,
        user_agent_rotation_frequency=5  # Rotate User-Agent every 5 requests
    )
    links = scraper.scrape_website(
        url=url,
        max_scrolls=10  # Set to None for unlimited scrolling
    )
    return list(links)

async def generate_product_grid_pages(href_links: List[str]) -> List[str]:
    # Your LLM-based implementation here
    batch_size = 10
    product_grid_pages = []
    llm = ChatOllama(
    model="llama3.1",
    temperature=0,
    base_url="https://11434-01j710tcmngbgrg8x0qjm1pazs.cloudspaces.litng.ai"
    # other params...
    )
    prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant that extracts the Product grid page specific links from given set of links.Remember the Product grid links will be unique, they will take the user directly to the products page when clicked.If there are no Links output Empty list",
        ),
        ("human", "Here are the list of Links: {input}"),
    ]
    )
    structured_llm = llm.with_structured_output(GridLinks)
    chain = prompt | structured_llm
    for chunk in chunk_list(href_links, batch_size):
        # Call your LLM-based function (assumed to be asynchronous)
        
        output = chain.invoke(
        {
            "input": f"{chunk}",
        }
        )
        product_grid_pages.extend(output.product_grid_links)
    return product_grid_pages

async def generate_product_pages(grid_page_urls: List[str]) -> List[str]:
    # Your LLM-based implementation here
    batch_size = 10
    product_grid_pages = []
    llm = ChatOllama(
    model="llama3.1",
    temperature=0,
    base_url="https://11434-01j710tcmngbgrg8x0qjm1pazs.cloudspaces.litng.ai"
    # other params...
    )
    prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant that extracts the Product specific links from given set of links.Remember the Product links will be unique and long,may contain some product id, they will take the user directly to the product when clicked.If there are no Links output Empty list",
        ),
        ("human", "Here are the list of Links: {input}"),
    ]
    )
    structured_llm = llm.with_structured_output(Links)
    chain = prompt | structured_llm
    for chunk in chunk_list(grid_page_urls, batch_size):
        # Call your LLM-based function (assumed to be asynchronous)
        
        output = chain.invoke(
        {
            "input": f"{chunk}",
        }
        )
        product_grid_pages.extend(output.product_links)
    return product_grid_pages

async def generate_mapping_file(website_to_product_mapping: Dict[str, List[str]], output_file: str) -> None:
    with open(output_file, "w") as file:
        for website, product_urls in website_to_product_mapping.items():
            file.write(f"{website}\n")
            for product_url in product_urls:
                file.write(f"  - {product_url}\n")
            file.write("\n")

# Orchestrating all functions asynchronously
async def process_website(session: aiohttp.ClientSession, url: str) -> List[str]:
    try:
        # Step 1: Extract all href links from the page
        print("GEtting all href Links")
        href_links = await get_all_href_links(session, url)

        # Step 2: Generate product grid page URLs
        print(href_links[:20])
        print("GEtting all grid Links")
        product_grid_pages = await generate_product_grid_pages(href_links[:20])
        print(product_grid_pages[:20])
        # Step 3: Generate product page URLs from grid page URLs
        print("Getting links from grid")
        all_grid_page_links = []

        for chunk in chunk_list(product_grid_pages[:3], 40):
            # For each chunk, process each URL individually
            for grid_url in chunk:
                print(f"Processing grid URL: {grid_url}")
                # Fetch href links from the grid URL
                grid_links = await get_all_href_links(session, grid_url)
                all_grid_page_links.extend(grid_links)  # Add the links to the final list
                print(f"Found {len(grid_links)} links from {grid_url}")
                

        # Step 2: Generate product grid page URLs
        print(all_grid_page_links[:20])

        print("GEtting all Product Links")
        product_pages = await generate_product_pages(all_grid_page_links[:20])
        print(product_pages[:20])
        return product_pages[:20]
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return []

async def main(website_urls: List[str], output_file: str):
    async with aiohttp.ClientSession() as session:
        # Step 4: Process all websites concurrently
        print("Processing Websites")
        tasks = [process_website(session, url) for url in website_urls]
        results = await asyncio.gather(*tasks)

        # Map each website to its corresponding product URLs
        website_to_product_mapping = {
            website_urls[i]: results[i] for i in range(len(website_urls))
        }

        # Step 5: Generate the mapping file
        await generate_mapping_file(website_to_product_mapping, output_file)

# Example usage
if __name__ == "__main__":
    urls = website_urls
    output_file = "website_product_mapping.txt"

    asyncio.run(main(urls, output_file))
