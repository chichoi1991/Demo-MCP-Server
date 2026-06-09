"""
Catalog loader for Network Config MCP Server.

Loads vendor/device configuration catalogs from JSON files in a data
directory. Each JSON file represents one vendor+model and contains the full
operational baseline configuration plus a list of reference documentation
links.

Resolution order for the data directory:
  1. NETWORK_CONFIG_DATA_DIR environment variable (if it points to a directory)
  2. /app/data (Docker container default)
  3. <repo>/data (local development)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_catalog: list[dict[str, Any]] = []


def _resolve_data_dir() -> Path:
    """Find the data directory containing vendor JSON files."""
    env_dir = os.environ.get("NETWORK_CONFIG_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.is_dir():
            return p
        logger.warning(
            "NETWORK_CONFIG_DATA_DIR=%s is not a directory; falling back to defaults",
            env_dir,
        )

    candidates = [
        Path("/app/data"),
        Path(__file__).resolve().parent.parent.parent / "data",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError(
        "Could not locate data directory. Set NETWORK_CONFIG_DATA_DIR or "
        "place vendor JSON files under /app/data or <repo>/data."
    )


def load_catalog() -> list[dict[str, Any]]:
    """Load all vendor catalog JSON files into memory. Idempotent."""
    global _catalog
    if _catalog:
        return _catalog

    data_dir = _resolve_data_dir()
    files = sorted(data_dir.glob("*.json"))
    if not files:
        logger.warning("No vendor JSON files found in %s", data_dir)

    loaded: list[dict[str, Any]] = []
    for path in files:
        try:
            with path.open("r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to load %s: %s", path, exc)
            continue

        if not isinstance(doc, dict) or "full_config" not in doc:
            logger.warning("Skipping %s: missing 'full_config' field", path)
            continue

        loaded.append(doc)
        logger.info(
            "Loaded catalog %s/%s (config=%d chars, refs=%d)",
            doc.get("vendor", "?"),
            doc.get("model", "?"),
            len(doc.get("full_config", "")),
            len(doc.get("references", [])),
        )

    _catalog = loaded
    return _catalog


def list_devices() -> list[dict[str, Any]]:
    """Return a summary of all loaded vendor/model devices."""
    return [
        {
            "vendor": c.get("vendor", ""),
            "model": c.get("model", ""),
            "model_display_name": c.get("model_display_name", ""),
            "os": c.get("os", ""),
            "os_release": c.get("os_release", ""),
            "config_size_chars": len(c.get("full_config", "")),
            "reference_count": len(c.get("references", [])),
        }
        for c in load_catalog()
    ]


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _aliases_match(query_norm: str, aliases: list[str]) -> bool:
    """True if any alias appears as a substring of the normalized query."""
    for alias in aliases or []:
        a = _normalize(alias)
        if a and a in query_norm:
            return True
    return False


def match_device(query: str) -> list[dict[str, Any]]:
    """
    Match a free-text query against the catalog by vendor and/or model alias.

    Scoring:
      vendor alias hit -> +1
      model alias hit  -> +2

    Returns every device with score >= 1 (i.e. at least vendor OR model
    matched), sorted by score descending. The full document (full_config +
    references) is included so the caller can return the complete operational
    baseline in one shot.
    """
    catalog = load_catalog()
    query_norm = _normalize(query)
    if not query_norm:
        return []

    results: list[dict[str, Any]] = []
    for doc in catalog:
        vendor = doc.get("vendor", "")
        model = doc.get("model", "")
        vendor_aliases = (doc.get("vendor_aliases") or []) + ([vendor] if vendor else [])
        model_aliases = (doc.get("model_aliases") or []) + ([model] if model else [])

        vendor_hit = _aliases_match(query_norm, vendor_aliases)
        model_hit = _aliases_match(query_norm, model_aliases)
        score = (1 if vendor_hit else 0) + (2 if model_hit else 0)

        if score < 1:
            continue

        results.append(
            {
                "vendor": vendor,
                "model": model,
                "model_display_name": doc.get("model_display_name", ""),
                "os": doc.get("os", ""),
                "os_release": doc.get("os_release", ""),
                "description": doc.get("description", ""),
                "full_config": doc.get("full_config", ""),
                "references": doc.get("references", []),
                "score": score,
            }
        )

    results.sort(key=lambda r: (-r["score"], r["vendor"], r["model"]))
    return results
