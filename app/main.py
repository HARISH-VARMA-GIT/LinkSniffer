import asyncio
import aiohttp
import os
import sys
from typing import List, Dict
from rich import print
from rich.console import Console
from dotenv import load_dotenv

from helpers.url_list import website_urls
from helpers.output_schemas import Links,GridLinks
from utils.dynamic_scraper import DynamicScraper
from utils.llm_manager import get_llm,Prompts

load_dotenv()
console = Console()

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
        max_scrolls=int(os.getenv("SCROLL_LIMIT",10)),
        max_links=int(os.getenv("PRODUCT_LINKS_LIMIT",None))  # Set to None for unlimited scrolling
    )

    return list(links)

 # Classify the links that redirect to product grid pages
async def generate_product_grid_pages(href_links: List[str]) -> List[str]:
    batch_size = int(os.getenv("BATCH_SIZE_PRODUCT_GRID_LINKS"))
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
    batch_size = int(os.getenv("BATCH_SIZE_PRODUCT_LINKS"))
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
async def process_website(session: aiohttp.ClientSession, url: str, max_links_per_stage: int = 10) -> List[str]:
    try:
        console.print("Getting all href Links",style="bold green")
        href_links = await get_all_href_links(session, url)
        if max_links_per_stage is not None:
            href_links = href_links[:max_links_per_stage]

        console.print("CLassifying grid Links",style="bold green")
        product_grid_pages = await generate_product_grid_pages(href_links)
        if max_links_per_stage is not None:
            product_grid_pages = product_grid_pages[:max_links_per_stage]
            print(product_grid_pages)
        
        console.print("Extracting Product Links",style="bold green")
        all_grid_page_links = []

        for chunk in chunk_list(product_grid_pages, 40):
            for grid_url in chunk:
                console.print(f"Processing grid URL: {grid_url}",style="yellow")

                grid_links = await get_all_href_links(session, grid_url)
                if max_links_per_stage is not None:
                    grid_links = grid_links[:max_links_per_stage]

                all_grid_page_links.extend(grid_links)  

                console.print(f"Found {len(grid_links)} links from {grid_url}",style="yellow")
                
        console.print("Classifying Product Links",style="bold green")
        if max_links_per_stage is not None:
            product_pages = await generate_product_pages(all_grid_page_links[:max_links_per_stage])
        else:
            product_pages = await generate_product_pages(all_grid_page_links)

        return product_pages
    except Exception as e:
        console.print(f"Error processing {url}: {e}",style = "red")
        return []

async def main(website_urls: List[str], output_file: str):
    async with aiohttp.ClientSession() as session:
        console.print("Processing Websites",style = "green")
        tasks = [process_website(session, url,max_links_per_stage=int(os.getenv("MAX_LINKS_PER_STAGE",None))) for url in website_urls]
        results = await asyncio.gather(*tasks)

        website_to_product_mapping = {
            website_urls[i]: results[i] for i in range(len(website_urls))
        }

        await generate_mapping_file(website_to_product_mapping, output_file)
        console.print("Output Text File is generated",style="magenta")

if __name__ == "__main__":
    urls = website_urls
    output_file = "website_product_mapping.txt"

    asyncio.run(main(urls, output_file))
