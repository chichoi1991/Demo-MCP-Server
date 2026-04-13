# News API MCP Server

A Model Context Protocol (MCP) server that provides access to global news articles through the [News API](https://newsapi.org/). This server implements a standardized interface for searching news articles, retrieving top headlines, and listing available news sources.

## Features

- Search for news articles on any topic with advanced filtering options
- Retrieve top headlines by country, category, or source
- Get information about available news sources with filtering by category, language, and country
- Built-in error handling and rate limit management

## Installation

### Using Claude Desktop

#### Installing via Docker

- Clone the repository and build a local image to be utilized by your Claude desktop client

```sh
cd news-api-mcp
docker build -t mcp/news-api .
```

- Change your `claude_desktop_config.json` to match the following, replacing `REPLACE_API_KEY` with your actual News API key:

> `claude_desktop_config.json` path
>
> - On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
> - On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "newsapi": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "-e",
        "NEWS_API_KEY",
        "mcp/news-api"
      ],
      "env": {
        "NEWS_API_KEY": "REPLACE_API_KEY"
      }
    }
  }
}
```

#### Installing via Smithery

To install News API MCP Server for Claude Desktop automatically via [Smithery](https://smithery.ai/):

```bash
npx -y @smithery/cli install @berlinbra/news-api-mcp --client claude
```

### Development Setup

#### Install packages

```
uv install -e .
```

#### Running

After connecting Claude client with the MCP tool via json file and installing the packages, Claude should see the server's mcp tools.

You can run the server yourself via:
```
uv run src/news_api_mcp/server.py
```

with inspector:
```
npx @modelcontextprotocol/inspector uv --directory /Users/{INSERT_USER}/YOUR/PATH/TO/news-api-mcp run src/news_api_mcp/server.py
```

## Available Tools

The server implements three tools:

### search-news

Search for news articles on any topic.

**Input Schema:**
```json
{
  "query": {
    "type": "string",
    "description": "Keywords or phrases to search for in the article title and body"
  },
  "from_date": {
    "type": "string",
    "description": "Start date for article search (YYYY-MM-DD format)"
  },
  "to_date": {
    "type": "string",
    "description": "End date for article search (YYYY-MM-DD format)"
  },
  "sources": {
    "type": "string",
    "description": "Comma-separated list of news sources to filter by (e.g., 'bbc-news,cnn')"
  },
  "language": {
    "type": "string",
    "description": "Language of the articles",
    "default": "en"
  },
  "sort_by": {
    "type": "string",
    "description": "Sort articles by relevancy, popularity, or publishedAt",
    "default": "publishedAt"
  },
  "page_size": {
    "type": "integer",
    "description": "Number of results to return per page (max 100)",
    "default": 20
  },
  "page": {
    "type": "integer",
    "description": "Page number for pagination",
    "default": 1
  }
}
```

**Example Response:**
```
Search results for 'artificial intelligence' (Found 28156 articles):

Article 1:
Title: OpenAI announces breakthrough in artificial intelligence reasoning
Source: TechCrunch
Author: John Smith
Published: 2025-03-25 14:30 UTC
Description: The AI research lab has developed a new model that demonstrates advanced reasoning capabilities...
URL: https://techcrunch.com/2025/03/25/openai-announces-new-ai-model/
---

Article 2:
...
```

### get-top-headlines

Retrieve breaking news headlines for countries, categories, and singular publishers.

**Input Schema:**
```json
{
  "country": {
    "type": "string",
    "description": "2-letter ISO 3166-1 country code"
  },
  "category": {
    "type": "string",
    "description": "Category to get headlines for"
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
    "default": 20
  },
  "page": {
    "type": "integer",
    "description": "Page number for pagination",
    "default": 1
  }
}
```

**Example Response:**
```
Top headlines for country: US, category: technology (Found 20 articles):

Article 1:
Title: Apple announces new MacBook Pro with M3 chip
Source: The Verge
Author: Alice Johnson
Published: 2025-03-28 13:45 UTC
Description: Apple has unveiled its latest MacBook Pro lineup featuring the new M3 chip...
URL: https://theverge.com/2025/03/28/apple-new-macbook-pro-m3
---

Article 2:
...
```

### get-news-sources

Retrieve information about the most notable news sources available.

**Input Schema:**
```json
{
  "category": {
    "type": "string",
    "description": "Find sources that display news of this category"
  },
  "language": {
    "type": "string",
    "description": "Find sources that display news in a specific language"
  },
  "country": {
    "type": "string",
    "description": "Find sources that display news in a specific country"
  }
}
```

**Example Response:**
```
Available news sources for category: technology, language: en (Found 22 sources):

Source 1:
Name: TechCrunch
ID: techcrunch
Description: TechCrunch is a leading technology media property, dedicated to obsessively profiling startups, reviewing new Internet products, and breaking tech news.
Category: technology
Language: en
Country: US
URL: https://techcrunch.com
---

Source 2:
...
```

## Error Handling

The server includes comprehensive error handling for various scenarios:

- Rate limit exceeded (News API free tier is limited to 100 requests per day)
- Invalid API key
- Network connectivity issues
- Timeout handling
- Malformed responses

Error messages are returned in a clear, human-readable format.

## Prerequisites

- Python 3.12 or higher
- httpx
- mcp

## Contributors

- [berlinbra](https://github.com/berlinbra)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This MCP server is licensed under the MIT License.
This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.
