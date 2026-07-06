"""
Utility Commands - Useful server utilities
"""

import discord
from discord.ext import commands
import asyncio
import platform
import psutil
import os
import time
from datetime import datetime, timezone, timedelta
from utils.helpers import make_embed, load_json, save_json

START_TIME = time.time()


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", aliases=["h", "commands"])
    async def help_command(self, ctx, *, command_name: str = None):
        """Show all commands or help for a specific command."""
        prefix = os.getenv("PREFIX", "!")

        if command_name:
            cmd = self.bot.get_command(command_name)
            if not cmd:
                return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Command `{command_name}` not found.", self.bot.error_color))
            embed = discord.Embed(title=f"📖 Command: {cmd.name}", color=0x5865F2)
            embed.add_field(name="Description", value=cmd.help or "No description.", inline=False)
            if cmd.aliases:
                embed.add_field(name="Aliases", value=", ".join(f"`{a}`" for a in cmd.aliases), inline=False)
            embed.add_field(name="Usage", value=f"`{prefix}{cmd.name} {cmd.signature}`", inline=False)
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title="📖 FangYuan V2 — Command Menu",
            description=f"Prefix: `{prefix}` | Use `{prefix}help <command>` for details",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        categories = {
            "<:strangerz_girl_staff:1523386969101697174> Moderation": [
                "ban", "unban", "tempban", "kick", "mute", "unmute",
                "warn", "warnings", "clearwarns", "purge", "lock", "unlock",
                "lockall", "slowmode", "nick", "addrole", "removerole", "nuke"
            ],
            "🎫 Tickets": [
                "ticketpanel", "ticketsetup", "addtoticket", "removefromticket", "ticketstats"
            ],
            "<a:ri_tada:1523620315325010092> Welcome": [
                "welcome", "leave", "autorole", "dmwelcome"
            ],
            "📝 Embeds": [
                "embed", "embedsend", "embeds", "embedload", "embeddelete", "say", "sayhere", "embedjson"
            ],
            "🤖 Autoresponder": [
                "ar add", "ar remove", "ar list", "ar enable", "ar disable", "ar info", "ar clear"
            ],
            "<a:Announce:1520896619829002240> Announcements": [
                "announce", "announceembed", "annrole", "broadcast", "setannchannel", "quickann", "updatelog"
            ],
            "<:x_leo_money:1523386970557120532> Crypto": [
                "ball", "cryptoinfo", "convert", "cryptotop", "gasfee"
            ],
            "<a:ri_tada:1523620315325010092> Giveaways": [
                "gstart", "gend", "greroll", "glist", "gdelete", "ginfo"
            ],
            "📊 Polls": [
                "poll", "quickpoll", "endpoll"
            ],
            "🎭 Roles": [
                "reactionrole", "rrremove", "rrlist", "massrole", "massunrole", "temprole"
            ],
            "ℹ️ Info": [
                "serverinfo", "userinfo", "roleinfo", "botinfo", "channelinfo", "avatar"
            ],
            "<a:Mod:1520895258118983743> Utility": [
                "ping", "uptime", "remind", "snipe", "editsnipe", "afk", "afklist", "inviteinfo"
            ],
        }

        for cat, cmds in categories.items():
            embed.add_field(name=cat, value=" ".join(f"`{c}`" for c in cmds), inline=False)

        embed.set_footer(text=f"FangYuan V2 • {len(list(self.bot.commands))} commands loaded")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping")
    async def ping(self, ctx):
        """Check bot latency."""
        start = time.perf_counter()
        msg = await ctx.send(embed=make_embed("🏓 Pinging...", 0x5865F2))
        end = time.perf_counter()
        api_latency = round((end - start) * 1000)
        ws_latency = round(self.bot.latency * 1000)

        embed = discord.Embed(title="🏓 Pong!", color=0x57F287)
        embed.add_field(name="WebSocket", value=f"`{ws_latency}ms`", inline=True)
        embed.add_field(name="API", value=f"`{api_latency}ms`", inline=True)
        quality = "<a:online:1523383854226870423> Excellent" if ws_latency < 100 else "🟡 Good" if ws_latency < 200 else "🔴 Poor"
        embed.add_field(name="Quality", value=quality, inline=True)
        await msg.edit(embed=embed)

    @commands.hybrid_command(name="uptime")
    async def uptime(self, ctx):
        """Show bot uptime."""
        delta = timedelta(seconds=int(time.time() - START_TIME))
        d, r = divmod(int(delta.total_seconds()), 86400)
        h, r = divmod(r, 3600)
        m, s = divmod(r, 60)
        uptime_str = f"{d}d {h}h {m}m {s}s"
        embed = discord.Embed(title="⏱️ Bot Uptime", description=f"**{uptime_str}**", color=0x5865F2)
        embed.add_field(name="Started At", value=f"<t:{int(START_TIME)}:F>", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="remind", aliases=["reminder", "remindme"])
    async def remind(self, ctx, duration: str, *, reminder: str):
        """Set a reminder. Usage: !remind 10m Take a break"""
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        duration = duration.lower()
        if duration[-1] in units and duration[:-1].isdigit():
            seconds = int(duration[:-1]) * units[duration[-1]]
        else:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Invalid duration. Use `10s`, `5m`, `2h`, `1d`.", self.bot.error_color))

        if seconds > 86400 * 7:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Maximum reminder duration is 7 days.", self.bot.error_color))

        fire_at = int(datetime.now(timezone.utc).timestamp()) + seconds
        embed = discord.Embed(
            title="⏰ Reminder Set",
            description=f"I'll remind you: **{reminder}**\nAt: <t:{fire_at}:F> (<t:{fire_at}:R>)",
            color=self.bot.success_color
        )
        await ctx.send(embed=embed)
        await asyncio.sleep(seconds)
        embed2 = discord.Embed(
            title="⏰ Reminder!",
            description=f"{ctx.author.mention}, you asked me to remind you:\n\n> **{reminder}**\n\nSet <t:{fire_at - seconds}:R>",
            color=0xFEE75C,
            timestamp=datetime.utcnow()
        )
        await ctx.send(content=ctx.author.mention, embed=embed2)

    # ─── SNIPE ────────────────────────────────────────────────────────────────

    _snipe_cache = {}
    _edit_snipe_cache = {}

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return
        self._snipe_cache[message.channel.id] = message

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content:
            return
        self._edit_snipe_cache[before.channel.id] = (before, after)

    @commands.hybrid_command(name="snipe", aliases=["s"])
    @commands.has_permissions(manage_messages=True)
    async def snipe(self, ctx):
        """Snipe the last deleted message in this channel."""
        msg = self._snipe_cache.get(ctx.channel.id)
        if not msg:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Nothing to snipe here.", self.bot.error_color))
        embed = discord.Embed(
            description=msg.content or "*[no text content]*",
            color=0xFEE75C,
            timestamp=msg.created_at
        )
        embed.set_author(name=str(msg.author), icon_url=msg.author.display_avatar.url)
        embed.set_footer(text=f"Deleted in #{ctx.channel.name}")
        if msg.attachments:
            embed.set_image(url=msg.attachments[0].url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="editsnipe", aliases=["esnipe"])
    @commands.has_permissions(manage_messages=True)
    async def editsnipe(self, ctx):
        """Snipe the last edited message in this channel."""
        result = self._edit_snipe_cache.get(ctx.channel.id)
        if not result:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Nothing to snipe here.", self.bot.error_color))
        before, after = result
        embed = discord.Embed(color=0x5865F2, timestamp=before.created_at)
        embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
        embed.add_field(name="Before", value=before.content[:1024] or "*[empty]*", inline=False)
        embed.add_field(name="After", value=after.content[:1024] or "*[empty]*", inline=False)
        embed.set_footer(text=f"Edited in #{ctx.channel.name}")
        await ctx.send(embed=embed)

    # ─── AFK ──────────────────────────────────────────────────────────────────

    _afk_data = {}

    @commands.hybrid_command(name="afk")
    async def afk(self, ctx, *, reason: str = "AFK"):
        """Set your AFK status."""
        self._afk_data[ctx.author.id] = {
            "reason": reason,
            "time": datetime.now(timezone.utc)
        }
        embed = discord.Embed(
            description=f"💤 **{ctx.author.display_name}** is now AFK: {reason}",
            color=0xFEE75C
        )
        await ctx.send(embed=embed)
        try:
            await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}"[:32])
        except Exception:
            pass

    @commands.hybrid_command(name="afklist")
    async def afklist(self, ctx):
        """Show all AFK users in this server."""
        afk_members = {uid: data for uid, data in self._afk_data.items() if ctx.guild.get_member(uid)}
        if not afk_members:
            return await ctx.send(embed=make_embed("No AFK members.", 0x5865F2))
        embed = discord.Embed(title="💤 AFK Members", color=0xFEE75C)
        for uid, data in afk_members.items():
            member = ctx.guild.get_member(uid)
            delta = datetime.now(timezone.utc) - data["time"]
            minutes = int(delta.total_seconds() // 60)
            embed.add_field(name=str(member), value=f"{data['reason']} ({minutes}m ago)", inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        # Remove AFK if they talk
        if message.author.id in self._afk_data:
            data = self._afk_data.pop(message.author.id)
            delta = datetime.now(timezone.utc) - data["time"]
            minutes = int(delta.total_seconds() // 60)
            embed = make_embed(f"👋 Welcome back {message.author.mention}! You were AFK for {minutes}m.", 0x57F287)
            await message.channel.send(embed=embed, delete_after=8)
            try:
                nick = message.author.display_name
                if nick.startswith("[AFK] "):
                    nick = nick[6:]
                await message.author.edit(nick=nick if nick != message.author.name else None)
            except Exception:
                pass

        # Notify about mentioned AFK users
        for user in message.mentions:
            if user.id in self._afk_data and user.id != message.author.id:
                data = self._afk_data[user.id]
                delta = datetime.now(timezone.utc) - data["time"]
                minutes = int(delta.total_seconds() // 60)
                embed = make_embed(f"💤 **{user.display_name}** is AFK: {data['reason']} ({minutes}m ago)", 0xFEE75C)
                await message.channel.send(embed=embed, delete_after=10)

    @commands.hybrid_command(name="inviteinfo", aliases=["invite"])
    async def inviteinfo(self, ctx, code: str = None):
        """Get info about a Discord invite link."""
        if not code:
            invites = await ctx.guild.invites()
            if not invites:
                return await ctx.send(embed=make_embed("No invites for this server.", 0x5865F2))
            embed = discord.Embed(title=f"📨 Server Invites ({len(invites)})", color=0x5865F2)
            for inv in invites[:10]:
                embed.add_field(
                    name=f"discord.gg/{inv.code}",
                    value=f"Uses: {inv.uses}\nCreated by: {inv.inviter or 'Unknown'}\nExpires: {'Never' if not inv.max_age else f'{inv.max_age}s'}",
                    inline=True
                )
            return await ctx.send(embed=embed)

        code = code.replace("https://discord.gg/", "").replace("discord.gg/", "")
        try:
            invite = await self.bot.fetch_invite(code, with_counts=True)
            embed = discord.Embed(title=f"📨 Invite: {code}", color=0x5865F2)
            if invite.guild:
                embed.add_field(name="Server", value=invite.guild.name, inline=True)
                embed.add_field(name="Members", value=f"{invite.approximate_member_count:,}", inline=True)
                embed.add_field(name="Online", value=f"{invite.approximate_presence_count:,}", inline=True)
                if invite.guild.icon:
                    embed.set_thumbnail(url=invite.guild.icon.url)
            embed.add_field(name="Channel", value=str(invite.channel), inline=True)
            embed.add_field(name="Inviter", value=str(invite.inviter) if invite.inviter else "Unknown", inline=True)
            await ctx.send(embed=embed)
        except discord.NotFound:
            await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Invalid or expired invite.", self.bot.error_color))

    @commands.hybrid_command(name="membercount", aliases=["mc"])
    async def membercount(self, ctx):
        """Show server member counts."""
        guild = ctx.guild
        total = guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        humans = total - bots
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)

        embed = discord.Embed(title=f"<:strangerz_girl_staff:1523386969101697174> {guild.name} — Member Count", color=0x5865F2)
        embed.add_field(name="Total", value=f"{total:,}", inline=True)
        embed.add_field(name="Humans", value=f"{humans:,}", inline=True)
        embed.add_field(name="Bots", value=f"{bots:,}", inline=True)
        embed.add_field(name="Online", value=f"{online:,}", inline=True)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="charinfo")
    async def charinfo(self, ctx, *, characters: str):
        """Get Unicode info about characters."""
        if len(characters) > 20:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Too many characters (max 20).", self.bot.error_color))
        lines = []
        for char in characters:
            cp = ord(char)
            name = unicodedata_name(char)
            lines.append(f"`\\U{cp:08X}` — **{name}** — `{char}`")
        await ctx.send(embed=discord.Embed(description="\n".join(lines), color=0x5865F2))

    @commands.hybrid_command(name="timestamp", aliases=["ts"])
    async def timestamp(self, ctx, *, dt_str: str = None):
        """Convert a date string to Discord timestamps."""
        if not dt_str:
            now = int(datetime.now(timezone.utc).timestamp())
            embed = discord.Embed(title="🕐 Current Timestamp", color=0x5865F2)
            embed.add_field(name="Unix", value=f"`{now}`", inline=False)
            embed.add_field(name="Short Time", value=f"<t:{now}:t> → `<t:{now}:t>`", inline=False)
            embed.add_field(name="Long Date/Time", value=f"<t:{now}:F> → `<t:{now}:F>`", inline=False)
            embed.add_field(name="Relative", value=f"<t:{now}:R> → `<t:{now}:R>`", inline=False)
            return await ctx.send(embed=embed)

        try:
            from dateutil import parser as dateparser
            dt = dateparser.parse(dt_str)
            ts = int(dt.timestamp())
        except Exception:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Couldn't parse date. Try `2025-01-01 12:00` or `January 1, 2025`.", self.bot.error_color))

        embed = discord.Embed(title="🕐 Timestamp", color=0x5865F2)
        embed.add_field(name="Unix", value=f"`{ts}`", inline=False)
        embed.add_field(name="Short Time", value=f"<t:{ts}:t> → `<t:{ts}:t>`", inline=True)
        embed.add_field(name="Short Date", value=f"<t:{ts}:d> → `<t:{ts}:d>`", inline=True)
        embed.add_field(name="Long Date/Time", value=f"<t:{ts}:F> → `<t:{ts}:F>`", inline=False)
        embed.add_field(name="Relative", value=f"<t:{ts}:R> → `<t:{ts}:R>`", inline=False)
        await ctx.send(embed=embed)


def unicodedata_name(char):
    try:
        import unicodedata
        return unicodedata.name(char)
    except Exception:
        return "Unknown"


async def setup(bot):
    await bot.add_cog(Utility(bot))
