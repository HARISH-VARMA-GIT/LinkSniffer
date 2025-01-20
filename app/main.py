import asyncio
import aiohttp
import os
from typing import List, Dict
from rich import print
from dotenv import load_dotenv

from helpers.url_list import website_urls
from helpers.output_schemas import Links,GridLinks
from utils.dynamic_scraper import DynamicScraper
from utils.llm_manager import get_llm,Prompts

load_dotenv()

GREEN = '\033[32m'
YELLOW = '\033[33m' 
RED = '\033[31m'
RESET = '\033[97m'

llm = get_llm()

def chunk_list(input_list, chunk_size):
    """Split a list into smaller chunks of a given size."""
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i:i + chunk_size]


## Get all href links by scrolling the website
async def get_all_href_links(session: aiohttp.ClientSession, url: str) -> List[str]:
    scraper = DynamicScraper(
        headless=True,
        scroll_pause=2,
        max_retries=3,
        user_agent_rotation_frequency=5  
    )

    links = scraper.scrape_website(
        url=url,
        max_scrolls=os.getenv("SCROLL_LIMIT",10),
        max_links=os.getenv("PRODUCT_LINKS_LIMIT")  # Set to None for unlimited scrolling
    )

    return list(links)

 # Classify the links that redirect to product grid pages
async def generate_product_grid_pages(href_links: List[str]) -> List[str]:
    batch_size = os.getenv("BATCH_SIZE_PRODUCT_GRID_LINKS")
    product_grid_pages = []
    prompt = Prompts.grid_page_prompt
    structured_llm = llm.with_structured_output(GridLinks)
    chain = prompt | structured_llm

    for chunk in chunk_list(href_links, batch_size):
        output = chain.invoke(
        {
            "input": f"{chunk}",
        }
        )
        product_grid_pages.extend(output.product_grid_links)

    return product_grid_pages


 # Classify the links that redirect to product pages
async def generate_product_pages(grid_page_urls: List[str]) -> List[str]:
    batch_size = os.getenv("BATCH_SIZE_PRODUCT_LINKS")
    product_grid_pages = []
    prompt = Prompts.product_page_prompt
    structured_llm = llm.with_structured_output(Links)
    chain = prompt | structured_llm

    for chunk in chunk_list(grid_page_urls, batch_size):
        output = chain.invoke(
        {
            "input": f"{chunk}",
        }
        )
        product_grid_pages.extend(output.product_links)

    return product_grid_pages

# make a text file which contains the website and respective product links
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
        print(GREEN+"Getting all href Links"+RESET)
        href_links = await get_all_href_links(session, url)

        print(GREEN+"CLassifying grid Links"+RESET)
        product_grid_pages = await generate_product_grid_pages(href_links)
        
        print(GREEN+"Extracting Product Links"+RESET)
        all_grid_page_links = []

        for chunk in chunk_list(product_grid_pages, 40):
            for grid_url in chunk:
                print(YELLOW+f"Processing grid URL: {grid_url}"+RESET)

                grid_links = await get_all_href_links(session, grid_url)
                all_grid_page_links.extend(grid_links)  

                print(YELLOW+f"Found {len(grid_links)} links from {grid_url}"+RESET)
                
        print(GREEN+"Classifying Product Links"+RESET)
        product_pages = await generate_product_pages(all_grid_page_links)

        return product_pages
    except Exception as e:
        print(RED+f"Error processing {url}: {e}"+RESET)
        return []

async def main(website_urls: List[str], output_file: str):
    async with aiohttp.ClientSession() as session:
        print(YELLOW+"Processing Websites"+RESET)
        tasks = [process_website(session, url) for url in website_urls]
        results = await asyncio.gather(*tasks)

        website_to_product_mapping = {
            website_urls[i]: results[i] for i in range(len(website_urls))
        }

        await generate_mapping_file(website_to_product_mapping, output_file)

if __name__ == "__main__":
    urls = website_urls
    output_file = "website_product_mapping.txt"

    asyncio.run(main(urls, output_file))
