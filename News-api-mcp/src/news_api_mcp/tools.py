"""
News API MCP Tools Module

This module contains utility functions for making requests to the News API
and formatting the responses.
"""

from typing import Any, Dict, List, Optional
import httpx
import os
import logging
import datetime

NEWS_API_BASE = "https://newsapi.org/v2"

# Per-request API key: set by HTTP handler from request header.
# Persists across requests so that if Copilot Studio sends the key
# only on initialize, it's still available for subsequent tools/call.
_current_request_api_key: str | None = None

def get_api_key() -> str | None:
    """Get the News API key: per-request header > environment variable."""
    key = _current_request_api_key or os.getenv('NEWS_API_KEY')
    logger.debug(f"get_api_key() → {'[set]' if key else '[MISSING]'} (source: {'header' if _current_request_api_key else 'env'})")
    return key

logger = logging.getLogger(__name__)

# Keep module-level API_KEY for backward compatibility (stdio mode)
API_KEY = os.getenv('NEWS_API_KEY')

async def make_news_api_request(
    client: httpx.AsyncClient, 
    endpoint: str, 
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any] | str:
    """Make a request to the News API with proper error handling.
    
    Args:
        client: An httpx AsyncClient instance
        endpoint: The News API endpoint to call (e.g., 'top-headlines', 'everything', 'sources')
        params: Parameters to include in the request
        
    Returns:
        Either a dictionary containing the API response, or a string with an error message
    """
    url = f"{NEWS_API_BASE}/{endpoint}"
    
    # Initialize params if None
    if params is None:
        params = {}
    
    # Add API key to params (per-request header takes priority over env var)
    api_key = get_api_key()
    if not api_key:
        return "NEWS_API_KEY not configured. Please provide it via the x-news-api-key header or NEWS_API_KEY environment variable."
    params["apiKey"] = api_key
    
    try:
        response = await client.get(
            url,
            params=params,
            timeout=30.0
        )
        
        # Check for specific error responses
        if response.status_code == 429:
            return "Rate limit exceeded. The News API has a limit of 100 requests per day for the free tier."
        elif response.status_code == 401:
            return "Unauthorized. API key invalid or expired."
        elif response.status_code == 400:
            return f"Bad request. Error details: {response.text}"
            
        response.raise_for_status()
        
        data = response.json()
        
        # Check for News API specific error messages
        if data.get("status") == "error":
            return f"News API error: {data.get('message', 'Unknown error')}"
            
        return data
    except httpx.TimeoutException:
        return "Request timed out after 30 seconds. The News API may be experiencing delays."
    except httpx.ConnectError:
        return "Failed to connect to News API. Please check your internet connection."
    except httpx.HTTPStatusError as e:
        return f"HTTP error occurred: {str(e)} - Response: {e.response.text}"
    except Exception as e:
        return f"Unexpected error occurred: {str(e)}"


def format_article(article: Dict[str, Any]) -> str:
    """Format article data into a concise string.
    
    Args:
        article: A single article from the News API response
        
    Returns:
        A formatted string containing the article information
    """
    try:
        # Extract and format the published date
        published_at = article.get("publishedAt", "")
        if published_at:
            try:
                date_obj = datetime.datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%Y-%m-%d %H:%M UTC")
            except (ValueError, TypeError):
                formatted_date = published_at
        else:
            formatted_date = "Unknown date"

        # Format the article data
        return (
            f"Title: {article.get('title', 'N/A')}\n"
            f"Source: {article.get('source', {}).get('name', 'N/A')}\n"
            f"Author: {article.get('author', 'N/A')}\n"
            f"Published: {formatted_date}\n"
            f"Description: {article.get('description', 'N/A')}\n"
            f"URL: {article.get('url', 'N/A')}\n"
            "---\n"
        )
    except Exception as e:
        return f"Error formatting article data: {str(e)}"


def format_articles(articles: List[Dict[str, Any]], limit: int = 5) -> str:
    """Format multiple articles into a concise string with limit.
    
    Args:
        articles: List of articles from the News API response
        limit: Maximum number of articles to include
        
    Returns:
        A formatted string containing the article information
    """
    try:
        if not articles:
            return "No articles found."
            
        # Limit the number of articles
        articles_limited = articles[:limit]
        
        # Format each article
        formatted = []
        for i, article in enumerate(articles_limited, 1):
            article_text = format_article(article)
            formatted.append(f"Article {i}:\n{article_text}")
            
        # Add information about omitted articles
        if len(articles) > limit:
            formatted.append(f"\n... and {len(articles) - limit} more articles")
            
        return "\n".join(formatted)
    except Exception as e:
        return f"Error formatting articles: {str(e)}"


def format_source(source: Dict[str, Any]) -> str:
    """Format news source information into a concise string.
    
    Args:
        source: A single news source from the News API response
        
    Returns:
        A formatted string containing the source information
    """
    try:
        return (
            f"Name: {source.get('name', 'N/A')}\n"
            f"ID: {source.get('id', 'N/A')}\n"
            f"Description: {source.get('description', 'N/A')}\n"
            f"Category: {source.get('category', 'N/A')}\n"
            f"Language: {source.get('language', 'N/A')}\n"
            f"Country: {source.get('country', 'N/A')}\n"
            f"URL: {source.get('url', 'N/A')}\n"
            "---\n"
        )
    except Exception as e:
        return f"Error formatting source data: {str(e)}"


def format_sources(sources: List[Dict[str, Any]], limit: int = 5) -> str:
    """Format multiple news sources into a concise string with limit.
    
    Args:
        sources: List of news sources from the News API response
        limit: Maximum number of sources to include
        
    Returns:
        A formatted string containing the source information
    """
    try:
        if not sources:
            return "No sources found."
            
        # Limit the number of sources
        sources_limited = sources[:limit]
        
        # Format each source
        formatted = []
        for i, source in enumerate(sources_limited, 1):
            source_text = format_source(source)
            formatted.append(f"Source {i}:\n{source_text}")
            
        # Add information about omitted sources
        if len(sources) > limit:
            formatted.append(f"\n... and {len(sources) - limit} more sources")
            
        return "\n".join(formatted)
    except Exception as e:
        return f"Error formatting sources: {str(e)}"
