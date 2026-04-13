"""
FRED API MCP Tools Module

Utility functions for making requests to the FRED (Federal Reserve Economic Data) API
and formatting the responses. Provides themed economic indicators for business insights.

API docs: https://fred.stlouisfed.org/docs/api/fred/
"""

from typing import Any, Dict, List, Optional
import httpx
import os
import logging
import datetime

FRED_API_BASE = "https://api.stlouisfed.org/fred"

# Per-request API key: set by HTTP handler from request header.
_current_request_api_key: str | None = None

logger = logging.getLogger(__name__)

# Module-level API_KEY for backward compatibility (stdio mode)
API_KEY = os.getenv('FRED_API_KEY')


def get_api_key() -> str | None:
    """Get the FRED API key: per-request header > environment variable."""
    key = _current_request_api_key or os.getenv('FRED_API_KEY')
    logger.debug(f"get_api_key() → {'[set]' if key else '[MISSING]'} (source: {'header' if _current_request_api_key else 'env'})")
    return key


# ── Series ID mappings by theme ──────────────────────────────────────

CONSUMER_DEMAND_SERIES = {
    "PCEDG": "Personal Consumption Expenditures: Durable Goods (Billions $)",
    "UMCSENT": "University of Michigan: Consumer Sentiment Index",
    "HOUST": "Housing Starts: Total New Privately Owned (Thousands)",
    "HSN1F": "New One Family Houses Sold (Thousands)",
    "TOTALSA": "Total Vehicle Sales (Millions)",
}

COST_PRESSURE_SERIES = {
    "DEXKOUS": "KRW/USD Exchange Rate",
    "DCOILWTICO": "Crude Oil Prices: WTI ($ per Barrel)",
    "WPUSI012011": "PPI: Copper and Copper Semimfg Products",
    "WPU101": "PPI: Iron and Steel",
    "PCU325211325211": "PPI: Plastics Material and Resins",
}

MACRO_ENVIRONMENT_SERIES = {
    "GDPC1": "Real GDP (Billions of Chained 2017 $)",
    "CPIAUCSL": "CPI: All Urban Consumers, All Items",
    "CPIDURASL": "CPI: Durables",
    "FEDFUNDS": "Federal Funds Effective Rate (%)",
    "UNRATE": "Unemployment Rate (%)",
    "DGS10": "10-Year Treasury Constant Maturity Rate (%)",
    "DGS2": "2-Year Treasury Constant Maturity Rate (%)",
}

INDUSTRY_PRODUCTION_SERIES = {
    "INDPRO": "Industrial Production Index (2017=100)",
    "DGORDER": "Manufacturers' New Orders: Durable Goods (Millions $)",
    "AMTMNO": "Manufacturers' New Orders: Total Manufacturing (Millions $)",
    "IPMAN": "Industrial Production: Manufacturing (2017=100)",
}

EV_ENERGY_SERIES = {
    "TOTALSA": "Total Vehicle Sales (Millions)",
    "AISRSA": "Auto Inventory/Sales Ratio",
    "DCOILWTICO": "Crude Oil Prices: WTI ($ per Barrel)",
    "GASREGW": "US Regular All Formulations Gas Price ($ per Gallon)",
    "IPG3361T3S": "Industrial Production: Motor Vehicles and Parts (2017=100)",
}

THEME_SERIES_MAP = {
    "consumer_demand": CONSUMER_DEMAND_SERIES,
    "cost_pressure": COST_PRESSURE_SERIES,
    "macro_environment": MACRO_ENVIRONMENT_SERIES,
    "industry_production": INDUSTRY_PRODUCTION_SERIES,
    "ev_energy": EV_ENERGY_SERIES,
}

PERIOD_MAP = {
    "6m": 183,
    "1y": 365,
    "3y": 1095,
    "5y": 1825,
}


async def make_fred_api_request(
    client: httpx.AsyncClient,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any] | str:
    """Make a request to the FRED API with proper error handling.

    Args:
        client: An httpx AsyncClient instance
        endpoint: FRED API endpoint path (e.g., 'series/observations')
        params: Query parameters to include in the request

    Returns:
        Either a dictionary containing the API response, or a string with an error message
    """
    url = f"{FRED_API_BASE}/{endpoint}"

    if params is None:
        params = {}

    api_key = get_api_key()
    if not api_key:
        return "FRED_API_KEY not configured. Please provide it via the x-fred-api-key header or FRED_API_KEY environment variable."

    params["api_key"] = api_key
    params.setdefault("file_type", "json")

    try:
        response = await client.get(url, params=params, timeout=30.0)

        if response.status_code == 429:
            return "Rate limit exceeded. Please wait before making more requests."
        elif response.status_code == 401:
            return "Unauthorized. FRED API key is invalid."
        elif response.status_code == 400:
            return f"Bad request: {response.text}"

        response.raise_for_status()

        data = response.json()

        if "error_message" in data:
            return f"FRED API error: {data['error_message']}"

        return data
    except httpx.TimeoutException:
        return "Request timed out after 30 seconds."
    except httpx.ConnectError:
        return "Failed to connect to FRED API. Please check your internet connection."
    except httpx.HTTPStatusError as e:
        return f"HTTP error: {e} - Response: {e.response.text}"
    except Exception as e:
        return f"Unexpected error: {e}"


def _calc_observation_start(period: str) -> str:
    """Calculate observation_start date from a period string."""
    days = PERIOD_MAP.get(period, 365)
    start = datetime.date.today() - datetime.timedelta(days=days)
    return start.isoformat()


async def fetch_series_observations(
    client: httpx.AsyncClient,
    series_id: str,
    period: str = "1y",
    units: str = "lin",
    frequency: Optional[str] = None,
    aggregation_method: str = "avg",
) -> Dict[str, Any] | str:
    """Fetch observation data for a single FRED series.

    Returns dict with keys: series_id, title, observations, units, frequency
    or a string error message.
    """
    # Get series metadata first
    meta = await make_fred_api_request(client, "series", {"series_id": series_id})
    if isinstance(meta, str):
        return meta

    series_info = meta.get("seriess", [{}])[0]
    title = series_info.get("title", series_id)
    native_freq = series_info.get("frequency_short", "")

    params: Dict[str, Any] = {
        "series_id": series_id,
        "observation_start": _calc_observation_start(period),
        "units": units,
        "sort_order": "desc",
    }
    if frequency:
        params["frequency"] = frequency
        params["aggregation_method"] = aggregation_method

    data = await make_fred_api_request(client, "series/observations", params)
    if isinstance(data, str):
        return data

    observations = data.get("observations", [])

    return {
        "series_id": series_id,
        "title": title,
        "native_frequency": native_freq,
        "units": units,
        "count": len(observations),
        "observations": observations,
    }


async def fetch_theme_data(
    client: httpx.AsyncClient,
    theme: str,
    indicator: Optional[str] = None,
    period: str = "1y",
    units: str = "lin",
) -> str:
    """Fetch data for a theme (group of related series) and return formatted text.

    Args:
        client: httpx async client
        theme: Theme key from THEME_SERIES_MAP
        indicator: Optional specific series_id within the theme (None = all)
        period: Time period (6m, 1y, 3y, 5y)
        units: Data transformation (lin, chg, pch, pc1, etc.)

    Returns:
        Formatted text string with all series data
    """
    series_map = THEME_SERIES_MAP.get(theme, {})
    if not series_map:
        return f"Unknown theme: {theme}"

    if indicator:
        if indicator not in series_map:
            available = ", ".join(series_map.keys())
            return f"Unknown indicator '{indicator}' for theme '{theme}'. Available: {available}"
        series_map = {indicator: series_map[indicator]}

    results = []
    for sid, description in series_map.items():
        result = await fetch_series_observations(client, sid, period=period, units=units)
        if isinstance(result, str):
            results.append(f"## {description} ({sid})\nError: {result}\n")
            continue
        results.append(format_series_result(result, description))

    return "\n".join(results)


def format_series_result(result: Dict[str, Any], description: str = "") -> str:
    """Format a single series observation result into readable text."""
    sid = result["series_id"]
    title = result["title"]
    units = result["units"]
    observations = result.get("observations", [])

    header = f"## {description or title} ({sid})"
    if not observations:
        return f"{header}\nNo data available for the requested period.\n"

    lines = [header]
    lines.append(f"Units: {units} | Data points: {result['count']}")
    lines.append("")

    # Show latest 10 observations (already sorted desc)
    display = observations[:10]
    for obs in display:
        date = obs.get("date", "N/A")
        value = obs.get("value", ".")
        lines.append(f"  {date}: {value}")

    if len(observations) > 10:
        oldest = observations[-1]
        lines.append(f"  ... ({len(observations) - 10} more data points)")
        lines.append(f"  {oldest.get('date', 'N/A')}: {oldest.get('value', '.')}")

    lines.append("---")
    return "\n".join(lines)


async def search_fred_series(
    client: httpx.AsyncClient,
    search_text: str,
    limit: int = 10,
    order_by: str = "popularity",
) -> str:
    """Search for FRED series by keyword and return formatted results."""
    params = {
        "search_text": search_text,
        "limit": limit,
        "order_by": order_by,
        "sort_order": "desc",
    }
    data = await make_fred_api_request(client, "series/search", params)
    if isinstance(data, str):
        return f"Search error: {data}"

    series_list = data.get("seriess", [])
    total = data.get("count", 0)

    if not series_list:
        return f"No series found for '{search_text}'."

    lines = [f"Search results for '{search_text}' (Total: {total}, showing {len(series_list)}):\n"]
    for i, s in enumerate(series_list, 1):
        lines.append(
            f"{i}. **{s.get('id', 'N/A')}** - {s.get('title', 'N/A')}\n"
            f"   Frequency: {s.get('frequency', 'N/A')} | Units: {s.get('units', 'N/A')}\n"
            f"   Last Updated: {s.get('last_updated', 'N/A')} | Popularity: {s.get('popularity', 'N/A')}\n"
        )

    return "\n".join(lines)
