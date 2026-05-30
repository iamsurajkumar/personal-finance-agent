# Finance Agent

An MCP (Model Context Protocol) server that gives an LLM-powered agent access to your investment portfolio — query positions, execute trades, and surface market news.

## Where you are now

**10 MCP tools** running on a single Python server:

### Portfolio queries (read-only)
| Tool | What it does |
|------|-------------|
| `get_position(symbol)` | Full detail on one holding: quantity, cost basis, current value, gain/loss |
| `get_portfolio_value()` | Total current value across all holdings |
| `get_total_cost_basis()` | Total amount invested |
| `get_total_gain_loss()` | Overall profit/loss with percentage |
| `get_largest_position()` | Biggest holding by current value |
| `list_all_holdings()` | Summary of every position |

### Trade execution
| Tool | What it does |
|------|-------------|
| `buy(symbol, quantity)` | Buy shares at current market price, updates CSV immediately, re-averages cost basis |
| `sell(symbol, quantity)` | Sell shares at current price, removes row if position closed |
| `check_order_status(order_id?)` | Look up one order or list all recent orders |

### Market intelligence
| Tool | What it does |
|------|-------------|
| `get_portfolio_news(symbol?)` | Alpha Vantage news for one ticker or all holdings, with sentiment labels |

### Architecture

```
Rasa (conversation layer)
  │ MCP protocol
  ▼
mcp/server.py          ← 10 tools registered here
  │
  ├── tools/           ← business logic per tool
  ├── services/        ← data, prices, orders, news
  └── sample_portfolio.csv  ← source of truth (5 holdings)
```

- **Prices:** Yahoo Finance (yfinance), fetched async on startup
- **News:** Alpha Vantage `NEWS_SENTIMENT` API
- **Trades:** In-memory order tracker (mock — Alpaca pending)

## Where you want to be

1. **Alpaca paper trading** — replace the mock `OrderService` with real Alpaca API calls for live order placement and status
2. **Rasa integration** — the MCP server is already built for Rasa's ReAct sub-agent; wire it into the hackathon bot
3. **Sector / currency analysis** — tools that infer sector from symbol and group holdings
4. **Multi-portfolio support** — `AgentContext` already supports it; add CSV switching
5. **Complex queries** — `run_custom_query` tool with pandas code generation for ad-hoc analysis
6. **Real-time price streaming** — periodic refresh instead of startup-only fetch
7. **Trade history** — track buy/sell timeline instead of current holdings snapshot

## Quick start

```bash
# 1. Clone and enter
cd finance-agent

# 2. Virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env:
#   PORTFOLIO_CSV_PATH=./sample_portfolio.csv
#   ALPHA_VANTAGE_API_KEY=your_free_key_from_https://alphavantage.co/support/#api-key

# 5. Test with MCP Inspector
npx @modelcontextprotocol/inspector python mcp/server.py
```

## Project structure

```
finance-agent/
├── mcp/
│   └── server.py           # MCP entry point, tool registration
├── tools/
│   ├── base.py             # AgentContext, formatting helpers
│   ├── position.py         # get_position
│   ├── portfolio.py        # value, cost_basis, gain_loss, largest, list
│   ├── trade.py            # buy, sell, check_order_status
│   └── news.py             # get_portfolio_news
├── services/
│   ├── data.py             # DataService: CSV load/query/write
│   ├── prices.py           # PriceService: Yahoo Finance fetch/cache
│   ├── order.py            # OrderService: in-memory order tracker
│   └── news.py             # NewsService: Alpha Vantage API wrapper
├── config.py               # Env vars (python-dotenv)
├── sample_portfolio.csv    # 5 holdings for testing
├── .env.example            # Config template
└── requirements.txt        # mcp, pandas, yfinance, python-dotenv, httpx
```

## CSV schema

```csv
symbol,quantity,cost_basis,purchase_date
AAPL,50,142.50,2023-06-15
```

| Column | Type | What it is |
|--------|------|------------|
| `symbol` | string | Stock ticker |
| `quantity` | int | Shares owned |
| `cost_basis` | float | Average price paid per share |
| `purchase_date` | date | YYYY-MM-DD |

Derived at runtime: `current_price` (Yahoo Finance), `current_value` (qty × price).
