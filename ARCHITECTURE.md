# Finance Agent Architecture

A finance agent that answers retrieval questions from a portfolio CSV, integrated with Rasa via MCP.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                           RASA                                  │
│                    (Conversation Layer)                         │
│                            │                                    │
│                            │ MCP Protocol                       │
│                            ▼                                    │
├─────────────────────────────────────────────────────────────────┤
│                     FINANCE MCP SERVER                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      mcp/server.py                        │  │
│  │                                                           │  │
│  │   AgentContext                                            │  │
│  │   ├── portfolio: DataService                              │  │
│  │   └── prices: PriceService                                │  │
│  │                                                           │  │
│  │   Tools:                                                  │  │
│  │   ├── get_position(symbol)                                │  │
│  │   ├── get_portfolio_value()                               │  │
│  │   ├── get_total_cost_basis()                              │  │
│  │   ├── get_total_gain_loss()                               │  │
│  │   ├── get_largest_position()                              │  │
│  │   └── list_all_holdings()                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────┐  ┌─────────────────────┐               │
│  │  services/data.py   │  │  services/prices.py │               │
│  │                     │  │                     │               │
│  │  - Load CSV         │  │  - Yahoo Finance    │               │
│  │  - Parse holdings   │  │  - Async fetch      │               │
│  │  - Pandas queries   │  │  - Cache in memory  │               │
│  └──────────┬──────────┘  └──────────┬──────────┘               │
│             │                        │                          │
│             ▼                        ▼                          │
│       portfolio.csv             Yahoo Finance API               │
└─────────────────────────────────────────────────────────────────┘
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data type | Investment portfolio (holdings snapshot) | User's use case |
| CSV schema | `symbol, quantity, cost_basis, purchase_date` | Minimal, derived fields computed |
| Derived fields | `current_value` from API, `sector/currency` from LLM | Avoid manual data entry |
| Price API | Yahoo Finance (yfinance) | Free, no key needed, good enough for hackathon |
| Price fetching | Async on startup, notify user if loading | Fast server start, no blocking |
| Framework | Claude SDK with tool use | Minimal abstraction, direct control |
| Integration | MCP server → Rasa ReAct sub-agent | Rasa hackathon requirement |
| Project structure | Layered (mcp / tools / services) | Clean separation of concerns |
| Data flow | Context object passed to tools | Explicit dependencies, testable |
| Error handling | Return human-readable strings | LLM-friendly, simple |
| Complex queries | Return "Support is coming" | Ship core first, expand later |
| Configuration | `.env` file with python-dotenv | Standard, simple |
| Dev workflow | `.env` + MCP Inspector | Test tools before Rasa integration |

## Project Structure

```
finance-agent/
├── mcp/
│   └── server.py           # MCP server entry point, tool definitions
├── tools/
│   ├── __init__.py
│   ├── position.py         # get_position tool
│   ├── portfolio.py        # portfolio-wide tools (value, cost basis, gain/loss, largest, list)
│   └── base.py             # shared tool utilities
├── services/
│   ├── __init__.py
│   ├── data.py             # DataService: CSV loading, pandas queries
│   └── prices.py           # PriceService: Yahoo Finance, async fetch, caching
├── config.py               # Environment variable loading
├── .env                    # Local config (gitignored)
├── .env.example            # Template for setup
├── sample_portfolio.csv    # Test data
├── requirements.txt        # Python dependencies
└── ARCHITECTURE.md         # This file
```

## CSV Schema

```csv
symbol,quantity,cost_basis,purchase_date
AAPL,50,142.50,2023-06-15
MSFT,30,285.00,2023-01-20
GOOGL,10,120.75,2024-02-10
```

| Column | Type | Description |
|--------|------|-------------|
| `symbol` | string | Stock ticker (e.g., AAPL) |
| `quantity` | integer | Number of shares owned |
| `cost_basis` | float | Average price paid per share |
| `purchase_date` | date | Date of purchase (YYYY-MM-DD) |

Derived at runtime:
- `current_price`: Fetched from Yahoo Finance
- `current_value`: `quantity × current_price`
- `sector`, `currency`: Inferred by LLM from symbol

## Tools

### get_position(symbol: str)
Returns position details for a specific stock.

**Example query:** "What's my AAPL position?"

**Response:** "AAPL: 50 shares @ $142.50 cost basis, current value $9,875.00"

---

### get_portfolio_value()
Returns total current value of all holdings.

**Example query:** "What's my portfolio worth?"

**Response:** "Total portfolio value: $48,250.00"

---

### get_total_cost_basis()
Returns total amount invested across all holdings.

**Example query:** "How much have I invested?"

**Response:** "Total cost basis: $35,000.00"

---

### get_total_gain_loss()
Returns overall profit/loss (current value - cost basis).

**Example query:** "Am I up or down overall?"

**Response:** "Total gain: $13,250.00 (+37.86%)"

---

### get_largest_position()
Returns the largest holding by current value.

**Example query:** "What's my biggest holding?"

**Response:** "Largest position: AAPL at $9,875.00 (20.5% of portfolio)"

---

### list_all_holdings()
Returns summary of all positions.

**Example query:** "Show me everything I own"

**Response:**
```
Holdings (3 positions):
- AAPL: 50 shares, $9,875.00
- MSFT: 30 shares, $12,450.00
- GOOGL: 10 shares, $1,520.00
```

## Component Details

### AgentContext

Central object holding shared dependencies, passed to all tools.

```python
@dataclass
class AgentContext:
    portfolio: DataService
    prices: PriceService
```

### DataService (services/data.py)

Loads and queries the portfolio CSV.

```python
class DataService:
    def __init__(self, csv_path: str): ...
    def get_all_holdings(self) -> pd.DataFrame: ...
    def get_holding(self, symbol: str) -> Optional[pd.Series]: ...
    def get_symbols(self) -> list[str]: ...
```

### PriceService (services/prices.py)

Fetches and caches stock prices from Yahoo Finance.

```python
class PriceService:
    def __init__(self): ...
    async def fetch_prices(self, symbols: list[str]) -> None: ...
    def get_price(self, symbol: str) -> Optional[float]: ...
    def is_ready(self) -> bool: ...
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORTFOLIO_CSV_PATH` | No | `portfolio.csv` | Path to portfolio CSV file |

### .env.example

```bash
# Path to your portfolio CSV file
PORTFOLIO_CSV_PATH=./sample_portfolio.csv
```

## Development Workflow

### 1. Setup

```bash
# Clone and enter project
cd finance-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your CSV path
```

### 2. Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python mcp/server.py
```

Opens browser UI to interactively test tools without Rasa.

### 3. Integrate with Rasa

See Rasa hackathon repo: https://github.com/RasaHQ/rasa-bos-hackathon-2026

The finance agent runs as an MCP tool server. Rasa's ReAct sub-agent discovers and calls the tools.

## Error Handling

Tools return human-readable error strings (not exceptions):

```python
def get_position(symbol: str, ctx: AgentContext) -> str:
    holding = ctx.portfolio.get_holding(symbol)
    if holding is None:
        return f"No position found for {symbol}"
    # ... return formatted position
```

This allows the LLM to respond naturally: "You don't seem to own XYZ. Did you mean...?"

## Future Enhancements

Items explicitly deferred:

- **Complex queries**: Currently returns "Support is coming". Future: add `run_custom_query` tool with pandas code generation.
- **Sector analysis**: `get_holdings_by_sector` tool (LLM infers sector from symbol).
- **Multiple portfolios**: Context object supports this, but not implemented.
- **Real-time prices**: Currently fetched once on startup. Future: periodic refresh or websocket.
- **Trade history**: Current schema is holdings snapshot. Future: support trade log CSV.

## Dependencies

```
mcp
pandas
yfinance
python-dotenv
```
