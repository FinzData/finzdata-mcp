"""Core data layer for the FinzData MCP server (free tier).

Standard library only. Every dated request is clipped to the last 365 days;
anything older returns an upgrade note pointing at the history bundles.
"""

import datetime
import json
import os
import urllib.error
import urllib.parse
import urllib.request

API_BASE = os.environ.get("FINZDATA_API_BASE", "https://api.finzdata.com").rstrip("/")
FREE_DAYS = 365
PRICING_URL = "https://finzdata.com/pricing"
SIGNUP_URL = "https://api.finzdata.com/"
MAX_ROWS = int(os.environ.get("FINZDATA_MCP_MAX_ROWS", "2000"))
USER_AGENT = "finzdata-mcp/0.1"


class FinzDataError(Exception):
    """Every user-facing failure raises this, with a plain-English message."""


def upgrade_note() -> str:
    """One-line note telling the user what the paid history bundle adds."""
    return (
        "FinzData's free tier covers the last 12 months. Full history (back to 2000 for "
        "stocks, every macro revision), 1-minute bars and daily updates come with a "
        "history bundle: " + PRICING_URL
    )


def _today() -> datetime.date:
    """The one clock seam: nothing else in this module reads the date."""
    return datetime.date.today()


def _parse_date(value):
    try:
        return datetime.date.fromisoformat(value)
    except (ValueError, TypeError):
        raise FinzDataError(f"bad date {value!r}: dates must be YYYY-MM-DD")


def free_window(start=None, end=None, today=None) -> dict:
    """Clip a start/end date range to the free tier's last-365-days window.

    Returns {"start": iso str, "end": iso str or None, "clipped": bool}.
    """
    if today is None:
        today = _today()
    floor = today - datetime.timedelta(days=FREE_DAYS)

    clipped = False
    if start is None:
        start_d = floor
    else:
        start_d = _parse_date(start)
        if start_d < floor:
            start_d = floor
            clipped = True

    if end is None:
        end_d = None
    else:
        end_d = _parse_date(end)
        if end_d < floor:
            raise FinzDataError(
                f"end date {end_d.isoformat()} is before the free tier window "
                f"(which starts {floor.isoformat()}). " + upgrade_note()
            )
        if end_d > today:
            end_d = today

    if end_d is not None and start_d > end_d:
        raise FinzDataError(
            f"start date {start_d.isoformat()} is after end date {end_d.isoformat()}"
        )

    return {
        "start": start_d.isoformat(),
        "end": end_d.isoformat() if end_d is not None else None,
        "clipped": clipped,
    }


def api_key():
    """The FinzData API key from the environment, or None if unset/blank."""
    key = os.environ.get("FINZDATA_API_KEY")
    if key is None:
        return None
    key = key.strip()
    return key or None


def _get(path: str, params: dict):
    """The one network seam: every tool calls the FinzData API through this."""
    key = api_key()
    if not key:
        raise FinzDataError(
            "No FinzData API key configured. Get a free API key at "
            + SIGNUP_URL
            + " and set the FINZDATA_API_KEY environment variable."
        )

    clean = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, bool):
            v = "true" if v else "false"
        clean[k] = v
    url = API_BASE + path + "?" + urllib.parse.urlencode(clean)

    req = urllib.request.Request(
        url,
        headers={
            "X-API-Key": key,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        detail = None
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict) and parsed.get("detail"):
                detail = str(parsed["detail"])
        except Exception:
            detail = None
        if not detail:
            detail = body[:300]
        code = e.code
        if code == 401:
            raise FinzDataError(
                "Your FinzData API key was not recognised. Check the key, or get a "
                "free API key at " + SIGNUP_URL
            )
        if code == 403:
            raise FinzDataError(
                f"FinzData refused this request: {detail}. See " + PRICING_URL
            )
        if code == 404:
            raise FinzDataError("not found: " + detail)
        if code == 429:
            raise FinzDataError(
                "You have hit the FinzData free tier daily limit. It resets tomorrow; "
                "higher limits are at " + PRICING_URL
            )
        raise FinzDataError(f"FinzData API error {code}: {detail}")
    except urllib.error.URLError as e:
        raise FinzDataError(f"could not reach FinzData: {e}")


def _rows(payload) -> list:
    """Normalise an API payload into a list of rows."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
        return [payload]
    return [payload]


def _result(payload, clipped=False, max_rows=None) -> dict:
    """Wrap rows in the standard result envelope returned to the assistant."""
    rows = _rows(payload)
    cap = max_rows or MAX_ROWS
    out = {
        "rows": rows[:cap],
        "row_count": len(rows),
        "truncated": len(rows) > cap,
        "free_tier_note": upgrade_note() if clipped else None,
        "source": "FinzData (finzdata.com)",
    }
    if out["truncated"]:
        out["note"] = (
            f"Showing the first {cap} of {len(rows)} rows; narrow the dates for the rest."
        )
    return out


def _need(value, what):
    if value is None or not str(value).strip():
        raise FinzDataError(f"{what} is required and cannot be blank")
    return str(value).strip().upper()


def prices_daily(symbol: str, start: str | None = None, end: str | None = None, adjust: str = "splits") -> dict:
    """Daily OHLCV bars for a stock symbol (e.g. AAPL). Returns one row per trading day with open, high, low, close and volume; prices are in the listing currency and `adjust` controls split/dividend adjustment ("splits" by default). On the free tier, history is limited to the last 12 months; older dates are clipped and the result carries a free_tier_note."""
    s = _need(symbol, "symbol")
    w = free_window(start, end)
    payload = _get(
        "/v1/prices/daily",
        {
            "symbol": s,
            "start": w["start"],
            "end": w["end"],
            "adjust": adjust,
            "format": "json",
        },
    )
    return _result(payload, w["clipped"])


def prices_intraday(symbol: str, start: str | None = None, end: str | None = None, interval: str = "1min", adjust: str = "none") -> dict:
    """Intraday OHLCV bars for a stock symbol at 1min, 5min or 1hour intervals. Returns timestamped rows with open, high, low, close and volume in the listing currency; if no start is given it defaults to the last 7 days. On the free tier, history is limited to the last 12 months."""
    if interval not in ("1min", "5min", "1hour"):
        raise FinzDataError(
            f"interval must be one of 1min, 5min, 1hour (got {interval!r})"
        )
    s = _need(symbol, "symbol")
    if start is None:
        start = (_today() - datetime.timedelta(days=7)).isoformat()
    w = free_window(start, end)
    payload = _get(
        "/v1/prices/minute",
        {
            "symbol": s,
            "start": w["start"],
            "end": w["end"],
            "interval": interval,
            "adjust": adjust,
            "format": "json",
        },
    )
    return _result(payload, w["clipped"])


def cot(market: str | None = None, code: str | None = None, report: str | None = None, start: str | None = None, end: str | None = None) -> dict:
    """Commitments of Traders (CFTC) positioning, weekly: long, short and net contracts by trader group for a futures market. Easiest use: market="gold" (a word from the market name) with report="legacy_fo", where large speculators are the non-commercial columns and hedgers the commercial ones; other reports are disagg_fo (managed money) and tff_fo (financial futures). Use cot_markets(query=...) to look up an exact code. Rows come newest week first. Counts are in contracts. On the free tier, only the last 12 months are returned."""
    w = free_window(start, end)
    payload = _get(
        "/v1/cot",
        {
            "market": market,
            "code": code,
            "report": report,
            "start": w["start"],
            "end": w["end"],
            "format": "json",
        },
    )
    rows = sorted(_rows(payload), key=lambda r: str(r.get("date", "")) if isinstance(r, dict) else "", reverse=True)
    out = _result(rows, w["clipped"])  # newest week first, so "right now" questions read the latest report
    if out["row_count"] == 0:
        out["note"] = "No rows matched. Check the market or code with cot_markets(query=...), or search by a word from the market name, e.g. market=\"gold\"."
    return out


def cot_markets(report: str = "legacy_fo", query: str | None = None) -> dict:
    """The list of futures markets available in the Commitments of Traders data, with each market's name and code, for a given report (default legacy_fo). Pass query (e.g. "gold", "s&p 500", "crude") to filter by market name; use the result's code or market with the cot tool. Note that dated COT history on the free tier is limited to the last 12 months."""
    rows = _rows(_get("/v1/cot/markets", {"report": report}))
    if query:
        q = query.strip().lower()
        rows = [r for r in rows if q in str(r.get("market", "")).lower() or q == str(r.get("code", "")).lower()]
    return _result(rows)


def macro(series: str, start: str | None = None, end: str | None = None) -> dict:
    """Time series for a macroeconomic indicator (e.g. CPIAUCSL for US CPI, UNRATE for unemployment). Returns one row per observation date with the value in the series' own units (index points, percent, millions, etc.). On the free tier, history is limited to the last 12 months; older dates are clipped."""
    s = _need(series, "series")
    w = free_window(start, end)
    payload = _get(
        "/v1/macro",
        {
            "series": s,
            "start": w["start"],
            "end": w["end"],
            "format": "json",
        },
    )
    return _result(payload, w["clipped"])


def macro_search(query: str | None = None, category: str | None = None, limit: int = 50) -> dict:
    """Search the catalogue of macroeconomic series by keyword (matched against the series id and title) and/or category. Returns matching series with their id, title, units and frequency, so you can pick a series id for the macro tool. Note that fetching a series' history on the free tier is limited to the last 12 months."""
    payload = _get("/v1/macro/series", {"category": category, "format": "json"})
    rows = _rows(payload)
    if query:
        q = str(query).lower()
        rows = [
            r
            for r in rows
            if isinstance(r, dict)
            and (q in str(r.get("id", "")).lower() or q in str(r.get("title", "")).lower())
        ]
    return _result(rows, max_rows=limit)


def short_interest(ticker: str, start: str | None = None, end: str | None = None) -> dict:
    """Short interest history for a stock ticker: one row per settlement date with shares sold short and related figures (share counts, not dollars). On the free tier, history is limited to the last 12 months; older dates are clipped."""
    t = _need(ticker, "ticker")
    w = free_window(start, end)
    payload = _get(
        "/v1/short_interest",
        {
            "ticker": t,
            "start": w["start"],
            "end": w["end"],
            "format": "json",
        },
    )
    return _result(payload, w["clipped"])


def insiders(ticker: str | None = None, owner: str | None = None, start: str | None = None, end: str | None = None) -> dict:
    """Insider transaction filings (buys, sells, option exercises) for a company ticker and/or an owner name. Returns one row per transaction with shares, price and value in the listing currency. On the free tier, history is limited to the last 12 months."""
    t = None
    if ticker is not None and str(ticker).strip():
        t = str(ticker).strip().upper()
    w = free_window(start, end)
    payload = _get(
        "/v1/insiders",
        {
            "ticker": t,
            "owner": owner,
            "start": w["start"],
            "end": w["end"],
            "format": "json",
        },
    )
    return _result(payload, w["clipped"])


def fund_holdings(ticker: str) -> dict:
    """The latest reported fund holdings for a ticker (most recent quarter only): which funds hold the stock, share counts and portfolio weights. Only the latest quarter is available on the free tier; deeper history is limited to the last 12 months and beyond that needs a history bundle."""
    t = _need(ticker, "ticker")
    payload = _get(
        "/v1/fund_holdings",
        {"ticker": t, "latest": True, "format": "json"},
    )
    return _result(payload)


def fundamentals(ticker: str, concept: str | None = None) -> dict:
    """Raw SEC XBRL facts a company reported in its 10-K/10-Q filings (columns: concept, unit, value, start, end, fy, fp, form, filed), optionally narrowed to one us-gaap concept such as NetIncomeLoss, Assets or RevenueFromContractWithCustomerExcludingAssessedTax. For ready-made income statements, balance sheets and cash flows use financial_statements instead. On the free tier, only filings from the last 12 months are returned."""
    t = _need(ticker, "ticker")
    payload = _get(
        "/v1/fundamentals",
        {"ticker": t, "concept": concept, "format": "json"},
    )
    return _result(payload)


def financial_statements(ticker: str, statement: str = "income", freq: str = "quarterly") -> dict:
    """Standardised financial statements for a US company from its SEC filings: statement is "income" (revenue, gross profit, operating income, net income, EPS, shares), "balance" (cash, assets, liabilities, equity) or "cashflow"; freq is "quarterly" or "annual". Values in US dollars, one row per period. On the free tier, only periods filed in the last 12 months are returned."""
    t = _need(ticker, "ticker")
    if statement not in ("income", "balance", "cashflow"):
        raise FinzDataError('statement must be "income", "balance" or "cashflow"')
    if freq not in ("quarterly", "annual"):
        raise FinzDataError('freq must be "quarterly" or "annual"')
    payload = _get("/v1/statements", {"ticker": t, "statement": statement, "freq": freq, "format": "json"})
    return _result(payload)


def company_profile(symbol: str) -> dict:
    """Reference profile for a US stock or ETF: name, exchange, sector, industry, country, state, IPO date, first and last date of price history, and whether it is delisted. Dated data elsewhere on the free tier is limited to the last 12 months."""
    s = _need(symbol, "symbol")
    payload = _get("/v1/profile", {"symbol": s, "format": "json"})
    return _result(payload)


def earnings_dates(ticker: str) -> dict:
    """Past earnings release dates for a ticker from SEC 8-K Item 2.02 filings: report date, filing time (US Eastern) and whether it came before the open or after the close. No EPS or forecasts. On the free tier, only the last 12 months are returned."""
    t = _need(ticker, "ticker")
    payload = _get("/v1/earnings_dates", {"ticker": t, "format": "json"})
    return _result(payload)


# Exposed over MCP: free-tier data only (intraday bars and 13F holdings are paid datasets, so not listed).
TOOLS = (
    "prices_daily",
    "cot",
    "cot_markets",
    "macro",
    "macro_search",
    "short_interest",
    "insiders",
    "fundamentals",
    "financial_statements",
    "company_profile",
    "earnings_dates",
)
