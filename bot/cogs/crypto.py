"""
Crypto Utility System
- Total received / spent all-time for an address
- .ball [address] — check pending/received in last 1 hour
Supports: ETH (Etherscan), BTC (Blockchain.info), BSC (BscScan), Polygon (Polygonscan)
"""

import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
from datetime import datetime, timezone, timedelta
from utils.helpers import make_embed

# ─── API KEYS (set in .env) ───────────────────────────────────────────────────
ETHERSCAN_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_KEY = os.getenv("BSCSCAN_API_KEY", "")
POLYGONSCAN_KEY = os.getenv("POLYGONSCAN_API_KEY", "")


def detect_chain(address: str):
    """Auto-detect chain from address format."""
    if address.startswith("0x") and len(address) == 42:
        return "eth"  # Could also be BSC or Polygon
    elif len(address) in (25, 26, 27, 28, 29, 30, 31, 32, 33, 34) and address[0] in ("1", "3", "b", "B"):
        return "btc"
    return "eth"


def wei_to_eth(wei: int) -> float:
    return wei / 1e18


def satoshi_to_btc(sats: int) -> float:
    return sats / 1e8


def format_crypto(amount: float, symbol: str) -> str:
    return f"{amount:,.6f} {symbol}"


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─── .ball COMMAND (special feature) ──────────────────────────────────────

    @commands.hybrid_command(name="ball", aliases=["cryptocheck", "addrcheck"])
    async def ball(self, ctx, address: str = None, chain: str = "auto"):
        """
        .ball [address] [chain]
        Check pending amounts and received in the last 1 hour.
        Chains: auto (default), eth, btc, bsc, matic
        """
        if not address:
            embed = discord.Embed(
                title="<:ownerinfo:1523725199457910884> .ball — Crypto Address Checker",
                description=(
                    "**Usage:** `.ball <address> [chain]`\n\n"
                    "**Supported chains:** `eth` `btc` `bsc` `matic`\n\n"
                    "**Example:**\n"
                    "`.ball 0x742d35Cc6634C0532925a3b844Bc454e4438f44e eth`\n"
                    "`.ball 1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf Na btc`"
                ),
                color=0xF0A500
            )
            return await ctx.send(embed=embed)

        async with ctx.typing():
            if chain == "auto":
                chain = detect_chain(address)

            chain = chain.lower()
            if chain in ("eth", "ethereum"):
                await self._ball_eth(ctx, address, "ETH", "https://api.etherscan.io/api", ETHERSCAN_KEY)
            elif chain in ("btc", "bitcoin"):
                await self._ball_btc(ctx, address)
            elif chain in ("bsc", "bnb", "binance"):
                await self._ball_eth(ctx, address, "BNB", "https://api.bscscan.com/api", BSCSCAN_KEY)
            elif chain in ("matic", "polygon"):
                await self._ball_eth(ctx, address, "MATIC", "https://api.polygonscan.com/api", POLYGONSCAN_KEY)
            else:
                await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Unknown chain `{chain}`. Use: `eth`, `btc`, `bsc`, `matic`.", self.bot.error_color))

    async def _ball_eth(self, ctx, address: str, symbol: str, api_url: str, api_key: str):
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        start_ts = int(one_hour_ago.timestamp())
        end_ts = int(now.timestamp())

        async with aiohttp.ClientSession() as session:
            # Get latest block for timestamp range
            try:
                # Get transactions
                params = {
                    "module": "account",
                    "action": "txlist",
                    "address": address,
                    "startblock": 0,
                    "endblock": 99999999,
                    "sort": "desc",
                    "apikey": api_key or "YourApiKeyToken"
                }
                async with session.get(api_url, params=params) as resp:
                    data = await resp.json()

                if data.get("status") != "1" and data.get("message") != "No transactions found":
                    if data.get("result") and "Invalid API Key" in str(data.get("result")):
                        await ctx.send(embed=make_embed(
                            f"<:ownerinfo:1523725199457910884> Etherscan/BscScan/PolygonScan API key not configured or invalid.\n"
                            f"Set `ETHERSCAN_API_KEY` in your `.env` file.",
                            self.bot.warning_color
                        ))
                        return

                txs = data.get("result", []) if isinstance(data.get("result"), list) else []

                # Filter last 1 hour
                recent_txs = [t for t in txs if int(t.get("timeStamp", 0)) >= start_ts]

                received_1h = sum(
                    int(t.get("value", 0))
                    for t in recent_txs
                    if t.get("to", "").lower() == address.lower() and t.get("isError", "0") == "0"
                )
                sent_1h = sum(
                    int(t.get("value", 0))
                    for t in recent_txs
                    if t.get("from", "").lower() == address.lower() and t.get("isError", "0") == "0"
                )
                gas_fees_1h = sum(
                    int(t.get("gasUsed", 0)) * int(t.get("gasPrice", 0))
                    for t in recent_txs
                    if t.get("from", "").lower() == address.lower() and t.get("isError", "0") == "0"
                )

                # All-time totals
                all_received = sum(
                    int(t.get("value", 0))
                    for t in txs
                    if t.get("to", "").lower() == address.lower() and t.get("isError", "0") == "0"
                )
                all_sent = sum(
                    int(t.get("value", 0))
                    for t in txs
                    if t.get("from", "").lower() == address.lower() and t.get("isError", "0") == "0"
                )

                # Get current balance
                bal_params = {
                    "module": "account",
                    "action": "balance",
                    "address": address,
                    "tag": "latest",
                    "apikey": api_key or "YourApiKeyToken"
                }
                async with session.get(api_url, params=bal_params) as bal_resp:
                    bal_data = await bal_resp.json()
                balance = int(bal_data.get("result", 0)) if bal_data.get("status") == "1" else 0

                # Get pending txs (unconfirmed pool)
                pending_params = {
                    "module": "account",
                    "action": "txlistinternal",
                    "address": address,
                    "startblock": 0,
                    "endblock": 99999999,
                    "sort": "desc",
                    "apikey": api_key or "YourApiKeyToken"
                }
                pending_received = 0
                try:
                    async with session.get(api_url, params=pending_params) as pend_resp:
                        pend_data = await pend_resp.json()
                    if isinstance(pend_data.get("result"), list):
                        pending_txs = [t for t in pend_data["result"] if int(t.get("timeStamp", 0)) >= start_ts]
                        pending_received = sum(
                            int(t.get("value", 0))
                            for t in pending_txs
                            if t.get("to", "").lower() == address.lower()
                        )
                except Exception:
                    pass

                # Get USD price
                usd_price = await self._get_price(session, symbol)

                # Build embed
                embed = discord.Embed(
                    title=f"<:ownerinfo:1523725199457910884> .ball — {symbol} Address Analysis",
                    color=0xF0A500,
                    timestamp=now
                )
                embed.set_thumbnail(url=self._chain_icon(symbol))

                short_addr = f"{address[:8]}...{address[-6:]}"
                embed.add_field(name="<:ownerinfo:1523725199457910884> Address", value=f"`{short_addr}`", inline=False)

                # Last 1 hour
                embed.add_field(
                    name="<:ownerinfo:1523725199457910884> Last 1 Hour",
                    value=(
                        f"<:ownerinfo:1523725199457910884> **Received:** {format_crypto(wei_to_eth(received_1h), symbol)}"
                        + (f" ≈ ${wei_to_eth(received_1h) * usd_price:,.2f}" if usd_price else "")
                        + f"\n<:ownerinfo:1523725199457910884> **Sent:** {format_crypto(wei_to_eth(sent_1h), symbol)}"
                        + f"\n<:ownerinfo:1523725199457910884> **Gas Fees:** {format_crypto(wei_to_eth(gas_fees_1h), symbol)}"
                        + f"\n<a:Poll:1523725207846781071> **Transactions:** {len(recent_txs)}"
                    ),
                    inline=False
                )

                embed.add_field(
                    name="<:ownerinfo:1523725199457910884> Pending (Internal, 1h)",
                    value=f"<:ownerinfo:1523725199457910884> {format_crypto(wei_to_eth(pending_received), symbol)}"
                    + (f" ≈ ${wei_to_eth(pending_received) * usd_price:,.2f}" if usd_price else ""),
                    inline=False
                )

                # All-time
                embed.add_field(
                    name="<a:Poll:1523725207846781071> All-Time Totals",
                    value=(
                        f"<a:tick:1523383850749792397> **Total Received:** {format_crypto(wei_to_eth(all_received), symbol)}"
                        + (f" ≈ ${wei_to_eth(all_received) * usd_price:,.2f}" if usd_price else "")
                        + f"\n<:x_leo_money:1523386970557120532> **Total Spent:** {format_crypto(wei_to_eth(all_sent), symbol)}"
                        + f"\n<:x_leo_money:1523386970557120532> **Current Balance:** {format_crypto(wei_to_eth(balance), symbol)}"
                        + (f" ≈ ${wei_to_eth(balance) * usd_price:,.2f}" if usd_price else "")
                        + f"\n<:ownerinfo:1523725199457910884> **Total TXs:** {len(txs)}"
                    ),
                    inline=False
                )

                explorer_url = {
                    "ETH": f"https://etherscan.io/address/{address}",
                    "BNB": f"https://bscscan.com/address/{address}",
                    "MATIC": f"https://polygonscan.com/address/{address}",
                }.get(symbol, "")
                if explorer_url:
                    embed.add_field(name="<:ownerinfo:1523725199457910884> Explorer", value=f"[View on Explorer]({explorer_url})", inline=False)

                embed.set_footer(text="FangYuan V2 Crypto • Data via blockchain explorers")
                await ctx.send(embed=embed)

            except aiohttp.ClientError as e:
                await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Network error: {e}", self.bot.error_color))
            except Exception as e:
                await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Error fetching data: {e}", self.bot.error_color))

    async def _ball_btc(self, ctx, address: str):
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"https://blockchain.info/rawaddr/{address}?limit=200") as resp:
                    if resp.status != 200:
                        return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Invalid BTC address or API error (status {resp.status}).", self.bot.error_color))
                    data = await resp.json()

                txs = data.get("txs", [])
                total_received = data.get("total_received", 0)
                total_sent = data.get("total_sent", 0)
                balance = data.get("final_balance", 0)
                n_tx = data.get("n_tx", 0)

                # Last 1 hour
                recent_received = 0
                recent_sent = 0
                pending_received = 0
                recent_tx_count = 0

                for tx in txs:
                    tx_time = tx.get("time", 0)
                    block_height = tx.get("block_height")
                    is_pending = block_height is None

                    # Calculate input/output for this address
                    addr_inputs = sum(
                        inp.get("prev_out", {}).get("value", 0)
                        for inp in tx.get("inputs", [])
                        if inp.get("prev_out", {}).get("addr") == address
                    )
                    addr_outputs = sum(
                        out.get("value", 0)
                        for out in tx.get("out", [])
                        if out.get("addr") == address
                    )

                    if is_pending:
                        pending_received += addr_outputs
                    elif tx_time >= int(one_hour_ago.timestamp()):
                        recent_received += addr_outputs
                        recent_sent += addr_inputs
                        recent_tx_count += 1

                usd_price = await self._get_price(session, "BTC")

                embed = discord.Embed(
                    title="<:ownerinfo:1523725199457910884> .ball — BTC Address Analysis",
                    color=0xF7931A,
                    timestamp=now
                )
                embed.set_thumbnail(url="https://bitcoin.org/img/icons/opengraph.png")

                short_addr = f"{address[:8]}...{address[-6:]}"
                embed.add_field(name="<:ownerinfo:1523725199457910884> Address", value=f"`{short_addr}`", inline=False)

                embed.add_field(
                    name="<:ownerinfo:1523725199457910884> Last 1 Hour",
                    value=(
                        f"<:ownerinfo:1523725199457910884> **Received:** {format_crypto(satoshi_to_btc(recent_received), 'BTC')}"
                        + (f" ≈ ${satoshi_to_btc(recent_received) * usd_price:,.2f}" if usd_price else "")
                        + f"\n<:ownerinfo:1523725199457910884> **Sent:** {format_crypto(satoshi_to_btc(recent_sent), 'BTC')}"
                        + f"\n<a:Poll:1523725207846781071> **Transactions:** {recent_tx_count}"
                    ),
                    inline=False
                )

                embed.add_field(
                    name="<:ownerinfo:1523725199457910884> Pending (Unconfirmed)",
                    value=f"<:ownerinfo:1523725199457910884> {format_crypto(satoshi_to_btc(pending_received), 'BTC')}"
                    + (f" ≈ ${satoshi_to_btc(pending_received) * usd_price:,.2f}" if usd_price else ""),
                    inline=False
                )

                embed.add_field(
                    name="<a:Poll:1523725207846781071> All-Time Totals",
                    value=(
                        f"<a:tick:1523383850749792397> **Total Received:** {format_crypto(satoshi_to_btc(total_received), 'BTC')}"
                        + (f" ≈ ${satoshi_to_btc(total_received) * usd_price:,.2f}" if usd_price else "")
                        + f"\n<:x_leo_money:1523386970557120532> **Total Spent:** {format_crypto(satoshi_to_btc(total_sent), 'BTC')}"
                        + f"\n<:x_leo_money:1523386970557120532> **Current Balance:** {format_crypto(satoshi_to_btc(balance), 'BTC')}"
                        + (f" ≈ ${satoshi_to_btc(balance) * usd_price:,.2f}" if usd_price else "")
                        + f"\n<:ownerinfo:1523725199457910884> **Total TXs:** {n_tx}"
                    ),
                    inline=False
                )

                embed.add_field(
                    name="<:ownerinfo:1523725199457910884> Explorer",
                    value=f"[View on Blockchain.com](https://blockchain.com/btc/address/{address})",
                    inline=False
                )
                embed.set_footer(text="FangYuan V2 Crypto • Data via Blockchain.info")
                await ctx.send(embed=embed)

            except aiohttp.ClientError as e:
                await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Network error: {e}", self.bot.error_color))
            except Exception as e:
                await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Error fetching BTC data: {e}", self.bot.error_color))

    # ─── GENERAL CRYPTO COMMANDS ──────────────────────────────────────────────

    @commands.hybrid_command(name="cryptoinfo", aliases=["coin", "crypto"])
    async def cryptoinfo(self, ctx, symbol: str = "bitcoin"):
        """Get current price and stats for a cryptocurrency."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}",
                    params={"localization": "false", "tickers": "false", "community_data": "false", "developer_data": "false"}
                ) as resp:
                    if resp.status == 404:
                        return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Coin `{symbol}` not found. Try the full name like `bitcoin`, `ethereum`.", self.bot.error_color))
                    data = await resp.json()

                mkt = data.get("market_data", {})
                price = mkt.get("current_price", {}).get("usd", 0)
                change_24h = mkt.get("price_change_percentage_24h", 0)
                change_7d = mkt.get("price_change_percentage_7d", 0)
                mkt_cap = mkt.get("market_cap", {}).get("usd", 0)
                volume = mkt.get("total_volume", {}).get("usd", 0)
                high_24h = mkt.get("high_24h", {}).get("usd", 0)
                low_24h = mkt.get("low_24h", {}).get("usd", 0)
                ath = mkt.get("ath", {}).get("usd", 0)
                rank = data.get("market_cap_rank", "N/A")
                name = data.get("name", symbol)
                sym = data.get("symbol", "").upper()
                icon = data.get("image", {}).get("small")

                color = 0x57F287 if change_24h >= 0 else 0xED4245
                arrow = "<a:Poll:1523725207846781071>" if change_24h >= 0 else "<a:Poll:1523725207846781071>"

                embed = discord.Embed(
                    title=f"{arrow} {name} ({sym})",
                    url=f"https://www.coingecko.com/en/coins/{symbol.lower()}",
                    color=color,
                    timestamp=datetime.utcnow()
                )
                if icon:
                    embed.set_thumbnail(url=icon)

                embed.add_field(name="<:x_leo_money:1523386970557120532> Price", value=f"${price:,.4f}", inline=True)
                embed.add_field(name="<a:Poll:1523725207846781071> Rank", value=f"#{rank}", inline=True)
                embed.add_field(name="<a:Poll:1523725207846781071> 24h Change", value=f"{change_24h:+.2f}%", inline=True)
                embed.add_field(name="<a:Poll:1523725207846781071> 7d Change", value=f"{change_7d:+.2f}%", inline=True)
                embed.add_field(name="<:ownerinfo:1523725199457910884> 24h High", value=f"${high_24h:,.4f}", inline=True)
                embed.add_field(name="<:ownerinfo:1523725199457910884> 24h Low", value=f"${low_24h:,.4f}", inline=True)
                embed.add_field(name="<:x_leo_money:1523386970557120532> Market Cap", value=f"${mkt_cap:,.0f}", inline=True)
                embed.add_field(name="<:ownerinfo:1523725199457910884> 24h Volume", value=f"${volume:,.0f}", inline=True)
                embed.add_field(name="<a:rizz_rewards:1523620313689100320> All-Time High", value=f"${ath:,.4f}", inline=True)
                embed.set_footer(text="FangYuan V2 Crypto • Powered by CoinGecko")
                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Error: {e}", self.bot.error_color))

    @commands.hybrid_command(name="convert", aliases=["cryptoconvert"])
    async def convert(self, ctx, amount: float, from_coin: str, to_coin: str = "usd"):
        """Convert between cryptocurrencies or to USD/EUR."""
        async with aiohttp.ClientSession() as session:
            try:
                url = "https://api.coingecko.com/api/v3/simple/price"
                params = {
                    "ids": from_coin.lower(),
                    "vs_currencies": to_coin.lower()
                }
                async with session.get(url, params=params) as resp:
                    data = await resp.json()

                if not data or from_coin.lower() not in data:
                    return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Couldn't find conversion for `{from_coin}` → `{to_coin}`.", self.bot.error_color))

                rate = data[from_coin.lower()].get(to_coin.lower())
                if rate is None:
                    return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> No rate found for `{to_coin}`.", self.bot.error_color))

                result = amount * rate
                embed = discord.Embed(
                    title="<:x_leo_money:1523386970557120532> Crypto Conversion",
                    description=f"`{amount:,} {from_coin.upper()}` = **`{result:,.6f} {to_coin.upper()}`**",
                    color=0x5865F2,
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text="FangYuan V2 Crypto • Powered by CoinGecko")
                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Error: {e}", self.bot.error_color))

    @commands.hybrid_command(name="cryptotop", aliases=["topcrypto", "topcoins"])
    async def cryptotop(self, ctx, limit: int = 10):
        """Show top cryptocurrencies by market cap."""
        limit = max(1, min(limit, 20))
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    "https://api.coingecko.com/api/v3/coins/markets",
                    params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": limit, "page": 1}
                ) as resp:
                    coins = await resp.json()

                embed = discord.Embed(
                    title=f"<a:rizz_rewards:1523620313689100320> Top {limit} Cryptocurrencies",
                    color=0xF0A500,
                    timestamp=datetime.utcnow()
                )
                lines = []
                for coin in coins:
                    change = coin.get("price_change_percentage_24h", 0) or 0
                    arrow = "<a:online:1523383854226870423>" if change >= 0 else "<:ownerinfo:1523725199457910884>"
                    lines.append(
                        f"**#{coin['market_cap_rank']}** {arrow} **{coin['name']}** ({coin['symbol'].upper()}) — "
                        f"${coin['current_price']:,.4f} | {change:+.2f}%"
                    )
                embed.description = "\n".join(lines)
                embed.set_footer(text="FangYuan V2 Crypto • Powered by CoinGecko")
                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Error: {e}", self.bot.error_color))

    @commands.hybrid_command(name="gasfee", aliases=["gas"])
    async def gasfee(self, ctx):
        """Check current ETH gas fees."""
        if not ETHERSCAN_KEY:
            return await ctx.send(embed=make_embed("<:ownerinfo:1523725199457910884> Etherscan API key not set. Add `ETHERSCAN_API_KEY` to `.env`.", self.bot.warning_color))
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    "https://api.etherscan.io/api",
                    params={"module": "gastracker", "action": "gasoracle", "apikey": ETHERSCAN_KEY}
                ) as resp:
                    data = await resp.json()

                if data.get("status") != "1":
                    return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Failed to fetch gas data.", self.bot.error_color))

                result = data["result"]
                embed = discord.Embed(
                    title="<:ownerinfo:1523725199457910884> Ethereum Gas Fees",
                    color=0x627EEA,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="<a:online:1523383854226870423> Low (Safe)", value=f"{result['SafeGasPrice']} Gwei", inline=True)
                embed.add_field(name="<:ownerinfo:1523725199457910884> Average", value=f"{result['ProposeGasPrice']} Gwei", inline=True)
                embed.add_field(name="<:ownerinfo:1523725199457910884> Fast", value=f"{result['FastGasPrice']} Gwei", inline=True)
                embed.set_footer(text="FangYuan V2 Crypto • Powered by Etherscan")
                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Error: {e}", self.bot.error_color))

    # ─── HELPERS ──────────────────────────────────────────────────────────────

    async def _get_price(self, session: aiohttp.ClientSession, symbol: str) -> float:
        """Get USD price for a symbol."""
        symbol_map = {
            "ETH": "ethereum",
            "BNB": "binancecoin",
            "MATIC": "matic-network",
            "BTC": "bitcoin",
        }
        coin_id = symbol_map.get(symbol.upper())
        if not coin_id:
            return 0
        try:
            async with session.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd"}
            ) as resp:
                data = await resp.json()
                return data.get(coin_id, {}).get("usd", 0)
        except Exception:
            return 0

    def _chain_icon(self, symbol: str) -> str:
        icons = {
            "ETH": "https://ethereum.org/static/6b935ac0e6194247347855dc3d328e83/eth-diamond-black.png",
            "BNB": "https://s2.coinmarketcap.com/static/img/coins/64x64/1839.png",
            "MATIC": "https://s2.coinmarketcap.com/static/img/coins/64x64/3890.png",
        }
        return icons.get(symbol, "")


async def setup(bot):
    await bot.add_cog(Crypto(bot))
