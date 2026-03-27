"""
Chiark MCP Server — Agent discovery and quality scoring.

Provides 5 tools for finding, scoring, and monitoring AI agents
across the A2A and MCP ecosystems via the chiark.ai API.

Usage:
    python -m chiark_mcp              # stdio transport (for Claude Code, Cursor)
    chiark-mcp                        # same, via console script

Hosted endpoint:
    https://chiark.ai/mcp/            # Streamable HTTP (for Smithery, registries)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logger = logging.getLogger(__name__)

API_BASE = "https://chiark.ai/api/v1"

server = Server("chiark")


async def _api_get(path: str, params: dict | None = None) -> dict | list | None:
    """Call the Chiark REST API."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(f"{API_BASE}{path}", params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"API call failed: {path} — {e}")
            return None


async def _api_post(path: str, body: dict) -> dict | None:
    """POST to the Chiark REST API."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{API_BASE}{path}", json=body)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"API POST failed: {path} — {e}")
            return None


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="find_agent",
            description=(
                "Find the best AI agents for a given task. Searches 2,000+ agents "
                "across A2A and MCP ecosystems. Supports quality constraints: "
                "min uptime, max latency, min score, auth requirement, payment support."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "What you need the agent for (e.g., 'web scraping', 'translation')",
                    },
                    "max_results": {"type": "integer", "description": "Max results (default 5)", "default": 5},
                    "min_score": {"type": "integer", "description": "Min operational score 0-100", "default": 0},
                    "min_uptime": {"type": "number", "description": "Min 30-day uptime fraction (e.g., 0.99 = 99%)"},
                    "max_latency_ms": {"type": "number", "description": "Max P95 latency in ms"},
                    "auth_required": {"type": "boolean", "description": "false = only open/unauthenticated agents"},
                    "payment_enabled": {"type": "boolean", "description": "Filter by x402 payment support"},
                    "protocol": {"type": "string", "description": "Filter by protocol: 'a2a' or 'mcp'"},
                    "category": {"type": "string", "description": "Filter by category (e.g., 'Developer Tools')"},
                },
                "required": ["task_description"],
            },
        ),
        Tool(
            name="check_agent_status",
            description=(
                "Check real-time status of an agent. Returns latest probe result: "
                "alive/dead, HTTP status, response time, TLS validity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent UUID from find_agent results"},
                },
                "required": ["agent_id"],
            },
        ),
        Tool(
            name="get_agent_score",
            description=(
                "Get full quality score breakdown: availability (0-30), conformance (0-30), "
                "performance (0-40), uptime, latency, trend, rank."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent UUID"},
                },
                "required": ["agent_id"],
            },
        ),
        Tool(
            name="report_outcome",
            description=(
                "Report routing outcome after using an agent. Helps improve "
                "future recommendations. Call after routing to an agent."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent UUID"},
                    "success": {"type": "boolean", "description": "Whether the agent completed the task"},
                    "error_message": {"type": "string", "description": "Error details if failed"},
                    "task_category": {"type": "string", "description": "Category (e.g., 'translation', 'crypto')"},
                },
                "required": ["agent_id", "success"],
            },
        ),
        Tool(
            name="get_ecosystem_stats",
            description=(
                "Ecosystem overview: total agents, online count, average scores, "
                "top categories, average latency."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "find_agent":
        params = {"page_size": arguments.get("max_results", 5)}
        task = arguments.get("task_description", "")
        if task:
            params["task"] = task
        for key in ("min_score", "min_uptime", "max_latency_ms", "auth_required", "payment_enabled", "protocol", "category"):
            if key in arguments and arguments[key] is not None:
                params[key] = arguments[key]

        data = await _api_get("/discover", params=params)
        if data is None:
            return [TextContent(type="text", text='{"error": "API unavailable"}')]

        agents = data.get("agents", []) if isinstance(data, dict) else []
        # Slim down for readability
        results = []
        for a in agents:
            results.append({
                "name": a.get("name"),
                "id": a.get("id"),
                "score": a.get("operational_score"),
                "max_score": a.get("max_score"),
                "uptime_30d": a.get("uptime_30d"),
                "p95_latency_ms": a.get("p95_latency_ms"),
                "protocol": a.get("protocol"),
                "endpoint_url": a.get("endpoint_url"),
                "categories": a.get("categories", []),
            })
        return [TextContent(type="text", text=json.dumps({"total": data.get("total", 0), "agents": results}, indent=2))]

    elif name == "check_agent_status":
        agent_id = arguments.get("agent_id", "")
        data = await _api_get(f"/agents/{agent_id}/status")
        if data is None:
            return [TextContent(type="text", text='{"error": "Agent not found or API unavailable"}')]
        return [TextContent(type="text", text=json.dumps(data, indent=2))]

    elif name == "get_agent_score":
        agent_id = arguments.get("agent_id", "")
        data = await _api_get(f"/agents/{agent_id}")
        if data is None:
            return [TextContent(type="text", text='{"error": "Agent not found or API unavailable"}')]
        # Return score breakdown
        result = {
            "name": data.get("name"),
            "operational_score": data.get("operational_score"),
            "max_score": data.get("max_score"),
            "score_breakdown": data.get("score_breakdown"),
            "uptime_30d": data.get("uptime_30d"),
            "p95_latency_ms": data.get("p95_latency_ms"),
            "conformance_status": data.get("conformance_status"),
            "trend": data.get("trend"),
            "protocol": data.get("protocol"),
            "categories": data.get("categories", []),
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "report_outcome":
        body = {
            "agent_id": arguments.get("agent_id"),
            "success": arguments.get("success", False),
        }
        if arguments.get("error_message"):
            body["error_message"] = arguments["error_message"]
        if arguments.get("task_category"):
            body["task_category"] = arguments["task_category"]

        data = await _api_post("/feedback", body)
        if data is None:
            return [TextContent(type="text", text='{"error": "Failed to record feedback"}')]
        return [TextContent(type="text", text=json.dumps(data, indent=2))]

    elif name == "get_ecosystem_stats":
        data = await _api_get("/stats")
        if data is None:
            return [TextContent(type="text", text='{"error": "API unavailable"}')]
        return [TextContent(type="text", text=json.dumps(data, indent=2))]

    else:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)
