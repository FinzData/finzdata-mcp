# FinzData MCP server

<!-- mcp-name: io.github.FinzData/finzdata-mcp -->

Research-grade US market data and server-side backtests for AI agents: Claude, ChatGPT, Gemini CLI, Cursor, Kimi, GLM and any MCP client.

**Remote server:** `https://api.finzdata.com/mcp` (Streamable HTTP, MCP 2026-07-28, accepts 2025-06-18 clients)
**Auth:** OAuth 2.1 with PKCE (sign in with your FinzData API key), or the header `Authorization: Bearer YOUR_API_KEY`
**Free key:** https://finzdata.com/signin · Pricing: https://finzdata.com/pricing · Agent docs: https://api.finzdata.com/agents.md

## Why FinzData for agents

- **Survivorship-free.** Universes include every company that traded on a date, delisted names included.
- **Point-in-time.** Every data tool takes `as_of`, so answers contain only what was public that day: fundamentals as filed, and macro series as first published (ALFRED vintages).
- **Backtests run on the server.** Describe a strategy and get back CAGR, volatility, Sharpe, drawdown, turnover, a benchmark, an equity curve, a reproducible `run_id` and a deflated Sharpe ratio that counts every variant you tried.

## Tools (all read-only)

| Tool | What it returns |
|---|---|
| `search_datasets` / `describe_dataset` | The catalog, fields and coverage |
| `get_universe` | Every US symbol trading on a date, or the 500/1000/3000 most-traded |
| `get_bars` | Daily and 1-minute OHLCV, split-adjusted |
| `get_fundamentals_pit` | Valuation and fundamentals as known on a date (P/E, EV/EBITDA, revenue, debt…) |
| `get_macro_vintage` | FRED/ALFRED series exactly as published by a date |
| `get_cot` | CFTC Commitments of Traders positioning |
| `get_13f` | Institutional holdings from 13F filings |
| `get_events` | Earnings dates, splits and economic releases |
| `run_backtest` | Momentum, MA cross, factor or formula strategies, long-only or long/short |
| `compare_runs` | Several backtests side by side |

## Connect

**Claude:** add FinzData from the Claude connector directory, or add a custom connector with `https://api.finzdata.com/mcp`.

**ChatGPT:** add the FinzData app from the ChatGPT directory, or add a connector in developer mode with the URL above.

**Gemini CLI:**
```bash
export FINZDATA_API_KEY=your-key
gemini extensions install https://github.com/FinzData/finzdata-mcp
```

**Cursor** (`.cursor/mcp.json`), **Windsurf, Cline, Kimi CLI, GLM / Z.ai coding tools and any client that takes a remote server:**
```json
{
  "mcpServers": {
    "finzdata": {
      "url": "https://api.finzdata.com/mcp",
      "headers": { "Authorization": "Bearer YOUR_API_KEY" }
    }
  }
}
```

**Clients that only run local (stdio) servers:** `pip install finzdata-mcp` (or `uvx finzdata-mcp`) with `FINZDATA_API_KEY` set. See [README.pypi.md](README.pypi.md).

## Example prompts

- "Backtest 12-1 momentum on the 500 most-traded US stocks since 2010, monthly, top 50, 10 bps costs."
- "What was the US unemployment rate for March 2020 as first reported?"
- "How are managed-money traders positioned in gold futures?"
- "Which institutions hold the most NVIDIA shares in the latest 13F quarter?"

## Plans

Free accounts cover the last 12 months, with 100 data calls and 5 backtests a day. Paid plans and prepaid credits ($0.001 per data call, $0.05 per backtest) unlock full history.

Data, not investment advice. Support: info@finzdata.com · https://finzdata.com/support · Privacy: https://finzdata.com/privacy
