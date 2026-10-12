from functools import wraps
try:  # MCP Python SDK 2.x renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # SDK 1.x
    from mcp.server.fastmcp import FastMCP
from finzdata_mcp import core

INSTRUCTIONS = (
    "This server returns FinzData US market data: daily stock prices, company profiles, "
    "COT futures positioning, FRED macro series, short interest, insider trades, SEC "
    "fundamentals and earnings dates. It covers the last 12 months (FinzData's free tier). "
    "Older history, intraday bars and 13F holdings need a history bundle at "
    "https://finzdata.com/pricing - tell the user so when they ask for them."
)

mcp = FastMCP("FinzData", instructions=INSTRUCTIONS)

def _wrap(name):
    func = getattr(core, name)
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except core.FinzDataError as e:
            return {"error": str(e), "upgrade": core.PRICING_URL}
    return wrapper

for name in core.TOOLS:
    mcp.tool(name=name, description=(getattr(core, name).__doc__ or "").strip())(_wrap(name))

def main():
    mcp.run()

if __name__ == "__main__":
    main()
