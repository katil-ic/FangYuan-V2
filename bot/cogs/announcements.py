"""
Announcements System - Rich announcement broadcasting
"""

import discord
from discord.ext import commands
from datetime import datetime
from utils.helpers import make_embed, load_json, save_json

ANN_FILE = "data/announcements.json"


class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="announce", aliases=["ann", "announcement"])
    @commands.has_permissions(manage_guild=True)
    async def announce(self, ctx, channel: discord.TextChannel, *, message: str):
        """Send a plain announcement to a channel."""
        embed = discord.Embed(
            title="📢 Announcement",
            description=message,
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Announced by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await channel.send(embed=embed)
        await ctx.send(embed=make_embed(f"✅ Announcement sent to {channel.mention}.", self.bot.success_color), delete_after=5)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="announceembed", aliases=["annedbed", "announcee"])
    @commands.has_permissions(manage_guild=True)
    async def announce_embed(self, ctx, channel: discord.TextChannel, ping: str = "none", *, message: str):
        """
        Send a rich embed announcement with optional ping.
        Ping options: none | here | everyone | @role
        """
        ping_content = None
        if ping.lower() == "here":
            ping_content = "@here"
        elif ping.lower() == "everyone":
            ping_content = "@everyone"
        elif ping.startswith("<@&"):
            ping_content = ping
        else:
            message = f"{ping} {message}" if ping.lower() != "none" else message

        embed = discord.Embed(
            title="📢 Announcement",
            description=message,
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Announced by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        await channel.send(content=ping_content, embed=embed)
        await ctx.send(embed=make_embed(f"✅ Announcement sent to {channel.mention}.", self.bot.success_color), delete_after=5)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="annrole", aliases=["announcerole"])
    @commands.has_permissions(manage_guild=True)
    async def announce_role(self, ctx, channel: discord.TextChannel, role: discord.Role, *, message: str):
        """Send an announcement pinging a specific role."""
        embed = discord.Embed(
            title="📢 Role Announcement",
            description=message,
            color=role.color.value or 0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Announced by {ctx.author}")
        await channel.send(content=role.mention, embed=embed)
        await ctx.send(embed=make_embed(f"✅ Sent to {channel.mention} with {role.mention} ping.", self.bot.success_color), delete_after=5)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="broadcast", aliases=["bcast"])
    @commands.has_permissions(administrator=True)
    async def broadcast(self, ctx, *, message: str):
        """Broadcast a message to ALL text channels the bot can send to."""
        confirm_embed = discord.Embed(
            title="⚠️ Broadcast Confirmation",
            description=f"This will send the following message to **all {len(ctx.guild.text_channels)}** text channels.\n\n>>> {message}\n\nReact with ✅ to confirm or ❌ to cancel.",
            color=self.bot.warning_color
        )
        confirm_msg = await ctx.send(embed=confirm_embed)
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        def check(r, u):
            return u == ctx.author and str(r.emoji) in ("✅", "❌") and r.message.id == confirm_msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30, check=check)
        except Exception:
            return await confirm_msg.edit(embed=make_embed("❌ Broadcast cancelled (timed out).", self.bot.error_color))

        if str(reaction.emoji) == "❌":
            return await confirm_msg.edit(embed=make_embed("❌ Broadcast cancelled.", self.bot.error_color))

        sent, failed = 0, 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.send(message)
                sent += 1
            except Exception:
                failed += 1

        await confirm_msg.edit(embed=make_embed(f"✅ Broadcast complete! Sent to **{sent}** channels. Failed: **{failed}**.", self.bot.success_color))

    @commands.command(name="setannchannel", aliases=["annchannel"])
    @commands.has_permissions(manage_guild=True)
    async def set_ann_channel(self, ctx, channel: discord.TextChannel):
        """Set the default announcement channel."""
        cfg = load_json(ANN_FILE)
        guild_id = str(ctx.guild.id)
        if guild_id not in cfg:
            cfg[guild_id] = {}
        cfg[guild_id]["channel_id"] = str(channel.id)
        save_json(ANN_FILE, cfg)
        await ctx.send(embed=make_embed(f"✅ Announcement channel set to {channel.mention}.", self.bot.success_color))

    @commands.command(name="quickann", aliases=["qa"])
    @commands.has_permissions(manage_guild=True)
    async def quickann(self, ctx, *, message: str):
        """Send announcement to the configured announcement channel."""
        cfg = load_json(ANN_FILE)
        guild_id = str(ctx.guild.id)
        channel_id = cfg.get(guild_id, {}).get("channel_id")
        if not channel_id:
            return await ctx.send(embed=make_embed("❌ No announcement channel set. Use `!setannchannel #channel`.", self.bot.error_color))
        channel = ctx.guild.get_channel(int(channel_id))
        if not channel:
            return await ctx.send(embed=make_embed("❌ Announcement channel not found.", self.bot.error_color))

        embed = discord.Embed(
            title="📢 Announcement",
            description=message,
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Announced by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await channel.send(embed=embed)
        await ctx.send(embed=make_embed(f"✅ Announcement sent to {channel.mention}.", self.bot.success_color), delete_after=5)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="updatelog", aliases=["changelog"])
    @commands.has_permissions(manage_guild=True)
    async def updatelog(self, ctx, channel: discord.TextChannel, version: str, *, changes: str):
        """Send a formatted changelog/update announcement."""
        items = [c.strip() for c in changes.split("|") if c.strip()]
        embed = discord.Embed(
            title=f"📋 Update — v{version}",
            color=0x57F287,
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        if items:
            embed.add_field(
                name="What's New",
                value="\n".join(f"• {item}" for item in items),
                inline=False
            )
        else:
            embed.description = changes
        embed.set_footer(text=f"Released by {ctx.author}")
        await channel.send(embed=embed)
        await ctx.send(embed=make_embed(f"✅ Changelog sent to {channel.mention}.", self.bot.success_color), delete_after=5)
        try:
            await ctx.message.delete()
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Announcements(bot))
