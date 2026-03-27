# Chiark MCP Server

MCP server for AI agent discovery and quality scoring. Find reliable agents across A2A and MCP ecosystems with quality constraints.

**Powered by [chiark.ai](https://chiark.ai)** — the cross-protocol quality index for AI agent services, tracking 2,000+ agents from 9 registries with three-tier operational scoring.

## Quick Start

### Use the hosted endpoint (recommended)

Add to your MCP client config (Claude Code, Cursor, etc.):

```json
{
  "mcpServers": {
    "chiark": {
      "url": "https://chiark.ai/mcp/"
    }
  }
}
```

### Install locally

```bash
pip install chiark-mcp
```

Add to your MCP client config:

```json
{
  "mcpServers": {
    "chiark": {
      "command": "chiark-mcp"
    }
  }
}
```

Or run directly:

```bash
python -m chiark_mcp
```

## Tools

### find_agent

Search for AI agents by task description with quality constraints.

```
find_agent(
  task_description="web scraping",
  min_uptime=0.95,
  max_latency_ms=500,
  protocol="mcp",
  max_results=5
)
```

Returns ranked agents with scores, uptime, latency, endpoint URLs.

### check_agent_status

Check if an agent is alive right now.

```
check_agent_status(agent_id="uuid-from-find-results")
```

Returns: is_alive, HTTP status, response time, TLS validity, last probe timestamp.

### get_agent_score

Get full quality score breakdown.

```
get_agent_score(agent_id="uuid")
```

Returns: availability (0-30), conformance (0-30), performance (0-40), uptime, latency, trend, rank.

### report_outcome

Report whether a routed agent succeeded or failed. Improves future recommendations.

```
report_outcome(agent_id="uuid", success=true, task_category="translation")
```

### get_ecosystem_stats

Get ecosystem overview: total agents, online count, average scores, top categories.

```
get_ecosystem_stats()
```

## How It Works

Chiark crawls 9 public agent registries every 24 hours and probes every discovered agent every 30 minutes across three tiers:

1. **Availability** — Is it alive? HTTP status, response time, TLS
2. **Conformance** — Does it follow its declared protocol correctly?
3. **Performance** — How fast does it respond? Task completion rate

Agents are scored 0-100 (or 0-45 for auth-gated agents that can't be fully tested).

## Constraint Filters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `min_score` | Minimum operational score (0-100) | `50` |
| `min_uptime` | Minimum 30-day uptime (0-1) | `0.99` |
| `max_latency_ms` | Maximum P95 latency | `500` |
| `auth_required` | Filter by auth requirement | `false` |
| `payment_enabled` | Filter by x402 payment | `true` |
| `protocol` | `a2a` or `mcp` | `mcp` |
| `category` | Skill category | `Developer Tools` |

## Links

- **Site**: https://chiark.ai
- **API docs**: https://chiark.ai/docs
- **Hosted MCP endpoint**: https://chiark.ai/mcp/
- **llms.txt**: https://chiark.ai/llms.txt
- **Agent Card**: https://chiark.ai/.well-known/agent.json

## License

MIT
