from typing import Any, List, Dict, Optional
import asyncio
import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import os

# Import functions from tools.py
from .tools import (
    make_news_api_request,
    format_articles,
    format_sources,
    API_KEY
)

if not API_KEY:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "NEWS_API_KEY environment variable not set. "
        "News API requests will fail until the key is configured."
    )

server = Server("news_api")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="search-news",
            description="Search for news articles on any topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords or phrases to search for in the article title and body",
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date for article search (YYYY-MM-DD format)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date for article search (YYYY-MM-DD format)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    },
                    "sources": {
                        "type": "string",
                        "description": "Comma-separated list of news sources to filter by (e.g., 'bbc-news,cnn')",
                    },
                    "language": {
                        "type": "string",
                        "description": "Language of the articles",
                        "enum": ["ar", "de", "en", "es", "fr", "he", "it", "nl", "no", "pt", "ru", "sv", "ud", "zh"],
                        "default": "en"
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort articles by relevancy, popularity, or publishedAt",
                        "enum": ["relevancy", "popularity", "publishedAt"],
                        "default": "publishedAt"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return per page (max 100)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                        "default": 1,
                        "minimum": 1
                    }
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get-top-headlines",
            description="Get top headlines by country, category, or source",
            inputSchema={
                "type": "object",
                "properties": {
                    "country": {
                        "type": "string",
                        "description": "2-letter ISO 3166-1 country code",
                        "enum": ["ae", "ar", "at", "au", "be", "bg", "br", "ca", "ch", "cn", "co", "cu", "cz", "de", "eg", "fr", "gb", "gr", "hk", "hu", "id", "ie", "il", "in", "it", "jp", "kr", "lt", "lv", "ma", "mx", "my", "ng", "nl", "no", "nz", "ph", "pl", "pt", "ro", "rs", "ru", "sa", "se", "sg", "si", "sk", "th", "tr", "tw", "ua", "us", "ve", "za"]
                    },
                    "category": {
                        "type": "string",
                        "description": "Category to get headlines for",
                        "enum": ["business", "entertainment", "general", "health", "science", "sports", "technology"]
                    },
                    "sources": {
                        "type": "string",
                        "description": "Comma-separated list of news source IDs (e.g., 'bbc-news,cnn')"
                    },
                    "query": {
                        "type": "string",
                        "description": "Keywords or phrases to search for in headlines"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return per page (max 100)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                        "default": 1,
                        "minimum": 1
                    }
                }
            },
        ),
        types.Tool(
            name="get-news-sources",
            description="Get available news sources",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Find sources that display news of this category",
                        "enum": ["business", "entertainment", "general", "health", "science", "sports", "technology"]
                    },
                    "language": {
                        "type": "string",
                        "description": "Find sources that display news in a specific language",
                        "enum": ["ar", "de", "en", "es", "fr", "he", "it", "nl", "no", "pt", "ru", "sv", "ud", "zh"]
                    },
                    "country": {
                        "type": "string",
                        "description": "Find sources that display news in a specific country",
                        "enum": ["ae", "ar", "at", "au", "be", "bg", "br", "ca", "ch", "cn", "co", "cu", "cz", "de", "eg", "fr", "gb", "gr", "hk", "hu", "id", "ie", "il", "in", "it", "jp", "kr", "lt", "lv", "ma", "mx", "my", "ng", "nl", "no", "nz", "ph", "pl", "pt", "ro", "rs", "ru", "sa", "se", "sg", "si", "sk", "th", "tr", "tw", "ua", "us", "ve", "za"]
                    }
                }
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can fetch news data and notify clients of changes.
    """
    if not arguments:
        return [types.TextContent(type="text", text="Missing arguments for the request")]

    if name == "search-news":
        query = arguments.get("query")
        if not query:
            return [types.TextContent(type="text", text="Missing query parameter")]

        # Extract and prepare the parameters
        params = {
            "q": query,
            "pageSize": arguments.get("page_size", 20),
            "page": arguments.get("page", 1),
            "language": arguments.get("language", "en"),
            "sortBy": arguments.get("sort_by", "publishedAt")
        }

        # Add optional parameters if provided
        if from_date := arguments.get("from_date"):
            params["from"] = from_date
            
        if to_date := arguments.get("to_date"):
            params["to"] = to_date
            
        if sources := arguments.get("sources"):
            params["sources"] = sources

        async with httpx.AsyncClient() as client:
            news_data = await make_news_api_request(
                client,
                "everything",
                params
            )

            if isinstance(news_data, str):
                return [types.TextContent(type="text", text=f"Error: {news_data}")]

            articles = news_data.get("articles", [])
            total_results = news_data.get("totalResults", 0)
            
            if not articles:
                return [types.TextContent(type="text", text=f"No articles found for query: '{query}'")]
                
            formatted_articles = format_articles(articles)
            
            result_text = f"Search results for '{query}' (Found {total_results} articles):\n\n{formatted_articles}"
            
            return [types.TextContent(type="text", text=result_text)]

    elif name == "get-top-headlines":
        # We need at least one parameter (country, category, source, or query)
        if not any(param in arguments for param in ["country", "category", "sources", "query"]):
            return [types.TextContent(
                type="text", 
                text="You must specify at least one of: country, category, sources, or query"
            )]

        # Extract and prepare the parameters
        params = {
            "pageSize": arguments.get("page_size", 20),
            "page": arguments.get("page", 1)
        }

        # Add optional parameters if provided
        for param_name in ["country", "category", "sources", "query"]:
            if param_value := arguments.get(param_name):
                # The API uses 'q' instead of 'query'
                key = "q" if param_name == "query" else param_name
                params[key] = param_value

        async with httpx.AsyncClient() as client:
            news_data = await make_news_api_request(
                client,
                "top-headlines",
                params
            )

            if isinstance(news_data, str):
                return [types.TextContent(type="text", text=f"Error: {news_data}")]

            articles = news_data.get("articles", [])
            total_results = news_data.get("totalResults", 0)
            
            if not articles:
                return [types.TextContent(type="text", text="No headlines found matching your criteria")]
                
            formatted_articles = format_articles(articles)
            
            # Create appropriate title based on parameters
            title_parts = []
            if country := arguments.get("country"):
                title_parts.append(f"country: {country.upper()}")
            if category := arguments.get("category"):
                title_parts.append(f"category: {category}")
            if sources := arguments.get("sources"):
                title_parts.append(f"sources: {sources}")
            if query := arguments.get("query"):
                title_parts.append(f"query: '{query}'")
                
            title = "Top headlines"
            if title_parts:
                title += " for " + ", ".join(title_parts)
                
            result_text = f"{title} (Found {total_results} articles):\n\n{formatted_articles}"
            
            return [types.TextContent(type="text", text=result_text)]

    elif name == "get-news-sources":
        # Extract and prepare the parameters
        params = {}

        # Add optional parameters if provided
        for param_name in ["category", "language", "country"]:
            if param_value := arguments.get(param_name):
                params[param_name] = param_value

        async with httpx.AsyncClient() as client:
            news_data = await make_news_api_request(
                client,
                "top-headlines/sources",
                params
            )

            if isinstance(news_data, str):
                return [types.TextContent(type="text", text=f"Error: {news_data}")]

            sources = news_data.get("sources", [])
            
            if not sources:
                return [types.TextContent(type="text", text="No news sources found matching your criteria")]
                
            formatted_sources = format_sources(sources)
            
            # Create appropriate title based on parameters
            title_parts = []
            if category := arguments.get("category"):
                title_parts.append(f"category: {category}")
            if language := arguments.get("language"):
                title_parts.append(f"language: {language}")
            if country := arguments.get("country"):
                title_parts.append(f"country: {country.upper()}")
                
            title = "Available news sources"
            if title_parts:
                title += " for " + ", ".join(title_parts)
                
            result_text = f"{title} (Found {len(sources)} sources):\n\n{formatted_sources}"
            
            return [types.TextContent(type="text", text=result_text)]
    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="news_api",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

# This is needed if you'd like to connect to a custom client
if __name__ == "__main__":
    asyncio.run(main())
