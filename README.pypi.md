# FinzData MCP server

<!-- mcp-name: io.github.FinzData/finzdata-mcp -->

US market data inside Claude, ChatGPT, Cursor and any MCP client.

## What you get

- prices_daily — daily OHLCV for US equities
- cot — Commitments of Traders reports
- cot_markets — available COT market codes
- macro — 10,000+ US economic series from FRED (inflation, jobs, rates, credit, consumer spending)
- macro_search — search macro series by keyword
- short_interest — short interest and days to cover
- insiders — insider transaction filings (Form 4)
- fundamentals — raw SEC XBRL facts by concept
- financial_statements — income statement, balance sheet and cash flow, quarterly or annual
- company_profile — company overview, sector, description
- earnings_dates — past earnings release dates and before/after-market timing

## Free tier

Every tool returns the last 12 months only. Older history (stocks back to 2000, every macro revision, 1-minute, 5-minute and hourly bars, 13F institutional holdings) comes with a history bundle: https://finzdata.com/pricing

## Setup

1. Get a free API key at https://api.finzdata.com/
2. Install: `pip install finzdata-mcp`
3. Add to your MCP client configuration:

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "finzdata": {
      "command": "finzdata-mcp",
      "env": {
        "FINZDATA_API_KEY": "your-key"
      }
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`): same JSON as above.

**No-install alternative**: `uvx finzdata-mcp`

## Example questions

- Chart NVDA's daily closes over the past year
- How are hedge funds positioned in gold futures?
- Which large caps have the highest short interest?
- How has US credit card debt changed this year?
- Which insiders bought or sold NVDA stock this year?

## Settings

- `FINZDATA_API_KEY` (required) — your FinzData API key
- `FINZDATA_MCP_MAX_ROWS` (default 2000) — maximum rows returned per tool call

---

Data, not investment advice. FinzData — Clean data. Real insights. Real alpha. https://finzdata.com
