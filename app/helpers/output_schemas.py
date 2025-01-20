from langchain_core.pydantic_v1 import BaseModel, Field

# schema for extracting product links
class Links(BaseModel):
    product_links: list = Field(description="The list of links containing only the product links")

# schema for extracting product grid page links
class GridLinks(BaseModel):
    product_grid_links: list = Field(description="The list of links containing the Products page")
