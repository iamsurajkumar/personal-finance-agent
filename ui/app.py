"""Streamlit dashboard for the Finance Agent."""

import asyncio
import sys
from pathlib import Path

# Add project root (parent of ui/) so we can import services/tools
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from config import Config
from services import DataService, PriceService, OrderService, NewsService
from tools.base import AgentContext, format_currency, format_percentage
from tools import (
    buy,
    sell,
    check_order_status,
    get_portfolio_news,
)

# ── Page config ────────────────────────────────────────────────────

st.set_page_config(
    page_title="Finance Agent",
    page_icon="💰",
    layout="wide",
)

# ── Helpers ────────────────────────────────────────────────────────

def _run(async_fn, *args, **kwargs):
    """Run an async function in Streamlit's sync world."""
    return asyncio.run(async_fn(*args, **kwargs))


@st.cache_resource
def init_services() -> AgentContext:
    """Create and cache services + context across Streamlit reruns."""
    ds = DataService(Config.PORTFOLIO_CSV_PATH)
    ds.load()

    ps = PriceService()
    symbols = ds.get_symbols()
    asyncio.run(ps.fetch_prices(symbols))

    osrv = OrderService()
    ns = NewsService(Config.ALPHA_VANTAGE_API_KEY) if Config.ALPHA_VANTAGE_API_KEY else None

    return AgentContext(portfolio=ds, prices=ps, orders=osrv, news=ns)


def reload_context():
    """Force-reload after a trade so the UI reflects CSV changes."""
    st.cache_resource.clear()
    st.rerun()


def holding_color(gain_pct: float) -> str:
    """Return CSS color string for gain/loss."""
    if gain_pct > 0:
        return "color: #00b894;"
    elif gain_pct < 0:
        return "color: #d63031;"
    return "color: #636e72;"


def gain_badge(gain_pct: float) -> str:
    """Return an emoji badge for a holding's performance."""
    if gain_pct > 50:
        return "🚀"
    elif gain_pct > 20:
        return "📈"
    elif gain_pct > 0:
        return "✅"
    elif gain_pct > -20:
        return "⚠️"
    return "🔻"


# ── Initialize services ────────────────────────────────────────────

ctx = init_services()

# ── Sidebar ────────────────────────────────────────────────────────

st.sidebar.title("💰 Finance Agent")
page = st.sidebar.radio(
    "Navigate",
    ["📊 Overview", "📋 Positions", "📈 Trade", "📰 News"],
)

st.sidebar.divider()
st.sidebar.caption(f"Portfolio: {ctx.portfolio.get_symbols().__len__()} holdings")
st.sidebar.caption(f"Prices: {'✅ Live' if ctx.prices.is_ready() else '⏳ Loading...'}")
st.sidebar.caption(f"News: {'✅ Ready' if ctx.news else '❌ No API key'}")

st.sidebar.divider()
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_resource.clear()

# ── Overview page ──────────────────────────────────────────────────

if page == "📊 Overview":
    st.title("Portfolio Overview")

    df = ctx.portfolio.get_all_holdings()
    total_cost = 0.0
    total_value = 0.0
    holding_data = []

    for _, row in df.iterrows():
        symbol = row["symbol"]
        qty = int(row["quantity"])
        cost = float(row["cost_basis"])
        price = ctx.prices.get_price(symbol)

        invested = qty * cost
        total_cost += invested
        if price:
            val = qty * price
            total_value += val
            gl = val - invested
            gl_pct = (gl / invested) * 100 if invested else 0
        else:
            gl_pct = 0

        holding_data.append({
            "symbol": symbol,
            "quantity": qty,
            "cost_basis": cost,
            "current_price": price or 0,
            "invested": invested,
            "current_value": price and (qty * price) or 0,
            "gain_loss_pct": gl_pct,
        })

    total_gl = total_value - total_cost
    total_gl_pct = (total_gl / total_cost) * 100 if total_cost else 0

    # Metric cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Portfolio Value", format_currency(total_value))
    with col2:
        st.metric("Total Invested", format_currency(total_cost))
    with col3:
        delta_str = f"{format_percentage(total_gl_pct)}"
        st.metric(
            "Gain / Loss",
            format_currency(total_gl),
            delta=delta_str,
        )
    with col4:
        st.metric("Holdings", len(holding_data))

    st.divider()

    # Holdings bar chart
    st.subheader("Holdings by Current Value")

    chart_data = sorted(holding_data, key=lambda h: h["current_value"], reverse=True)
    import plotly.express as px
    fig = px.bar(
        chart_data,
        x="symbol",
        y="current_value",
        color="gain_loss_pct",
        color_continuous_scale=["#d63031", "#dfe6e9", "#00b894"],
        labels={"symbol": "", "current_value": "Current Value ($)", "gain_loss_pct": "Gain/Loss %"},
        text_auto=".2s",
    )
    fig.update_layout(coloraxis_showscale=False, height=350)
    st.plotly_chart(fig, use_container_width=True)

    # Quick holdings cards
    st.subheader("Holdings")
    cols = st.columns(len(holding_data))
    for i, h in enumerate(holding_data):
        with cols[i]:
            badge = gain_badge(h["gain_loss_pct"])
            gl_color = "#00b894" if h["gain_loss_pct"] >= 0 else "#d63031"
            sign = "+" if h["gain_loss_pct"] >= 0 else ""
            st.markdown(
                f"""<div style="padding: 0.5rem; border-radius: 8px;
                border: 1px solid #ddd; text-align: center;">
                <strong>{badge} {h['symbol']}</strong><br>
                <span style="font-size: 1.2rem;">{format_currency(h['current_value'])}</span><br>
                <small style="color:{gl_color};">{sign}{h['gain_loss_pct']:.1f}%</small>
                </div>""",
                unsafe_allow_html=True,
            )

# ── Positions page ─────────────────────────────────────────────────

elif page == "📋 Positions":
    st.title("Positions")

    df = ctx.portfolio.get_all_holdings()
    rows = []

    for _, row in df.iterrows():
        symbol = row["symbol"]
        qty = int(row["quantity"])
        cost = float(row["cost_basis"])
        price = ctx.prices.get_price(symbol)

        invested = qty * cost
        if price:
            current_val = qty * price
            gl = current_val - invested
            gl_pct = (gl / invested) * 100 if invested else 0
            gl_str = f"{'+' if gl >= 0 else ''}{format_currency(gl)} ({'+' if gl_pct >= 0 else ''}{gl_pct:.1f}%)"
            price_str = format_currency(price)
            value_str = format_currency(current_val)
        else:
            current_val = 0
            gl_str = "N/A"
            price_str = "N/A"
            value_str = "N/A"

        rows.append({
            "Symbol": symbol,
            "Shares": qty,
            "Avg Cost": format_currency(cost),
            "Current Price": price_str,
            "Invested": format_currency(invested),
            "Current Value": value_str,
            "Gain / Loss": gl_str,
            "Purchase Date": row["purchase_date"].strftime("%Y-%m-%d"),
        })

    st.dataframe(
        rows,
        use_container_width=True,
        column_config={
            "Symbol": st.column_config.TextColumn(width="small"),
            "Gain / Loss": st.column_config.TextColumn(width="medium"),
        },
    )

    st.divider()
    st.caption(f"Source: {Config.PORTFOLIO_CSV_PATH}")

# ── Trade page ────────────────────────────────────────────────────

elif page == "📈 Trade":
    st.title("Trade")

    tab1, tab2 = st.tabs(["Execute Trade", "Order History"])

    with tab1:
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            symbol = st.text_input("Symbol", placeholder="AAPL").upper()
        with col2:
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
        with col3:
            st.write("")  # spacer
            st.write("")

        # Show current position if symbol exists
        if symbol:
            holding = ctx.portfolio.get_holding(symbol)
            current_price = ctx.prices.get_price(symbol)
            if holding is not None and current_price:
                q = int(holding["quantity"])
                v = q * current_price
                st.info(
                    f"Current: **{q} shares** of {symbol} "
                    f"@ {format_currency(current_price)} = {format_currency(v)}"
                )
            elif holding is not None and not current_price:
                st.info(f"Current: **{int(holding['quantity'])} shares** of {symbol} (price unavailable)")
            elif current_price:
                st.info(f"New position: {symbol} is trading at {format_currency(current_price)}")
            else:
                if st.button(f"🔍 Fetch {symbol} Price"):
                    with st.spinner(f"Fetching {symbol}..."):
                        price = _run(ctx.prices.fetch_one, symbol)
                    if price:
                        st.success(f"{symbol} is trading at {format_currency(price)}")
                        reload_context()
                    else:
                        st.error(f"Could not fetch price for {symbol}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🟢 Buy", use_container_width=True, type="primary"):
                if not symbol:
                    st.error("Enter a symbol")
                else:
                    with st.spinner(f"Buying {quantity} {symbol}..."):
                        result = _run(buy, symbol, quantity, ctx)
                    if "Error" in result:
                        st.error(result)
                    else:
                        st.success(result)
                    reload_context()

        with col2:
            if st.button("🔴 Sell", use_container_width=True):
                if not symbol:
                    st.error("Enter a symbol")
                else:
                    with st.spinner(f"Selling {quantity} {symbol}..."):
                        result = _run(sell, symbol, quantity, ctx)
                    if "Error" in result:
                        st.error(result)
                    else:
                        st.success(result)
                    reload_context()

    with tab2:
        orders = ctx.orders.list_all()
        if not orders:
            st.info("No orders placed this session.")
        else:
            order_rows = []
            for o in orders:
                order_rows.append({
                    "ID": o["id"],
                    "Side": o["side"].upper(),
                    "Symbol": o["symbol"],
                    "Quantity": o["quantity"],
                    "Fill Price": format_currency(o["fill_price"]),
                    "Total": format_currency(o["quantity"] * o["fill_price"]),
                    "Status": o["status"].title(),
                    "Time": o["filled_at"],
                })
            st.dataframe(order_rows, use_container_width=True, hide_index=True)

# ── News page ──────────────────────────────────────────────────────

elif page == "📰 News":
    st.title("Portfolio News")

    symbols = ctx.portfolio.get_symbols()

    # Optional ticker filter
    filter_symbol = st.selectbox(
        "Filter by ticker",
        ["All holdings"] + symbols,
    )

    if filter_symbol != "All holdings":
        lookup = filter_symbol
    else:
        lookup = None

    if st.button("📰 Fetch News", type="primary"):
        if ctx.news is None:
            st.warning(
                "News not configured. Add ALPHA_VANTAGE_API_KEY to your .env file."
            )
        else:
            with st.spinner("Fetching news..."):
                result = _run(get_portfolio_news, lookup, ctx)

            if "News unavailable" in result or "error" in result.lower():
                st.warning(result)
            else:
                st.markdown(result)
    else:
        st.info("Click 'Fetch News' to load the latest headlines.")
