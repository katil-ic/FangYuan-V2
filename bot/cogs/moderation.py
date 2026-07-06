"""
Moderation Cog - Full server moderation suite
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from utils.helpers import make_embed, load_json, save_json, format_duration

WARNS_FILE = "data/warns.json"


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─── BAN ──────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="ban", aliases=["b"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(embed=make_embed("❌ You cannot ban someone with equal or higher role.", self.bot.error_color))
        try:
            await member.send(embed=make_embed(f"You have been **banned** from **{ctx.guild.name}**.\nReason: {reason}", self.bot.error_color))
        except Exception:
            pass
        await member.ban(reason=f"{ctx.author}: {reason}")
        await ctx.send(embed=make_embed(f"🔨 **{member}** has been banned.\nReason: {reason}", self.bot.success_color))
        await self._log(ctx.guild, "Ban", ctx.author, member, reason)

    @commands.hybrid_command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason="No reason provided"):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"{ctx.author}: {reason}")
            await ctx.send(embed=make_embed(f"✅ **{user}** has been unbanned.", self.bot.success_color))
        except discord.NotFound:
            await ctx.send(embed=make_embed("❌ That user is not banned.", self.bot.error_color))

    @commands.hybrid_command(name="tempban", aliases=["tb"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def tempban(self, ctx, member: discord.Member, duration: str, *, reason="No reason provided"):
        seconds = parse_time(duration)
        if not seconds:
            return await ctx.send(embed=make_embed("❌ Invalid duration. Use e.g. `1d`, `2h`, `30m`", self.bot.error_color))
        try:
            await member.send(embed=make_embed(
                f"You have been **temp-banned** from **{ctx.guild.name}** for `{duration}`.\nReason: {reason}",
                self.bot.error_color
            ))
        except Exception:
            pass
        await member.ban(reason=f"Tempban ({duration}): {ctx.author}: {reason}")
        await ctx.send(embed=make_embed(f"🔨 **{member}** has been temp-banned for `{duration}`.", self.bot.success_color))
        await asyncio.sleep(seconds)
        try:
            await ctx.guild.unban(member, reason="Tempban expired")
        except Exception:
            pass

    # ─── KICK ─────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="kick", aliases=["k"])
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(embed=make_embed("❌ You cannot kick someone with equal or higher role.", self.bot.error_color))
        try:
            await member.send(embed=make_embed(f"You have been **kicked** from **{ctx.guild.name}**.\nReason: {reason}", self.bot.warning_color))
        except Exception:
            pass
        await member.kick(reason=f"{ctx.author}: {reason}")
        await ctx.send(embed=make_embed(f"👢 **{member}** has been kicked.\nReason: {reason}", self.bot.success_color))
        await self._log(ctx.guild, "Kick", ctx.author, member, reason)

    # ─── MUTE / TIMEOUT ───────────────────────────────────────────────────────

    @commands.hybrid_command(name="mute", aliases=["timeout", "to"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: str = "10m", *, reason="No reason provided"):
        seconds = parse_time(duration)
        if not seconds:
            return await ctx.send(embed=make_embed("❌ Invalid duration. Use e.g. `1d`, `2h`, `30m`", self.bot.error_color))
        until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        await member.timeout(until, reason=f"{ctx.author}: {reason}")
        await ctx.send(embed=make_embed(f"🔇 **{member}** has been muted for `{duration}`.\nReason: {reason}", self.bot.success_color))
        await self._log(ctx.guild, "Mute", ctx.author, member, reason, extra=f"Duration: {duration}")

    @commands.hybrid_command(name="unmute", aliases=["untimeout"])
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await member.timeout(None, reason=f"{ctx.author}: {reason}")
        await ctx.send(embed=make_embed(f"🔊 **{member}** has been unmuted.", self.bot.success_color))

    # ─── WARN ─────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="warn", aliases=["w"])
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        warns = load_json(WARNS_FILE)
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        if guild_id not in warns:
            warns[guild_id] = {}
        if user_id not in warns[guild_id]:
            warns[guild_id][user_id] = []
        warns[guild_id][user_id].append({
            "reason": reason,
            "moderator": str(ctx.author),
            "timestamp": datetime.utcnow().isoformat()
        })
        save_json(WARNS_FILE, warns)
        count = len(warns[guild_id][user_id])
        try:
            await member.send(embed=make_embed(
                f"⚠️ You have been **warned** in **{ctx.guild.name}**.\nReason: {reason}\nTotal Warnings: {count}",
                self.bot.warning_color
            ))
        except Exception:
            pass
        await ctx.send(embed=make_embed(f"⚠️ **{member}** has been warned. (Total: **{count}**)\nReason: {reason}", self.bot.warning_color))
        await self._log(ctx.guild, "Warn", ctx.author, member, reason, extra=f"Total Warnings: {count}")

    @commands.hybrid_command(name="warnings", aliases=["warns", "warnlist"])
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member):
        warns = load_json(WARNS_FILE)
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        user_warns = warns.get(guild_id, {}).get(user_id, [])
        if not user_warns:
            return await ctx.send(embed=make_embed(f"✅ **{member}** has no warnings.", self.bot.success_color))
        embed = discord.Embed(
            title=f"⚠️ Warnings for {member}",
            color=self.bot.warning_color,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        for i, w in enumerate(user_warns, 1):
            embed.add_field(
                name=f"Warning #{i}",
                value=f"**Reason:** {w['reason']}\n**By:** {w['moderator']}\n**Date:** {w['timestamp'][:10]}",
                inline=False
            )
        embed.set_footer(text=f"Total: {len(user_warns)} warning(s)")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clearwarns", aliases=["warnreset"])
    @commands.has_permissions(administrator=True)
    async def clearwarns(self, ctx, member: discord.Member):
        warns = load_json(WARNS_FILE)
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        if guild_id in warns and user_id in warns[guild_id]:
            warns[guild_id][user_id] = []
            save_json(WARNS_FILE, warns)
        await ctx.send(embed=make_embed(f"✅ Cleared all warnings for **{member}**.", self.bot.success_color))

    # ─── PURGE ────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="purge", aliases=["clear", "prune"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int, member: discord.Member = None):
        if amount < 1 or amount > 1000:
            return await ctx.send(embed=make_embed("❌ Amount must be between 1 and 1000.", self.bot.error_color))
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if member:
            def check(m):
                return m.author == member
            deleted = await ctx.channel.purge(limit=amount * 5, check=check, bulk=True)
            deleted = deleted[:amount]
        else:
            deleted = await ctx.channel.purge(limit=amount)
        msg = await ctx.send(embed=make_embed(f"🗑️ Deleted **{len(deleted)}** messages.", self.bot.success_color))
        await asyncio.sleep(4)
        await msg.delete()

    # ─── LOCKDOWN ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="lock", aliases=["lockdown"])
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None, *, reason="No reason"):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(embed=make_embed(f"🔒 **{channel.mention}** has been locked.\nReason: {reason}", self.bot.error_color))

    @commands.hybrid_command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(embed=make_embed(f"🔓 **{channel.mention}** has been unlocked.", self.bot.success_color))

    @commands.hybrid_command(name="lockall")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lockall(self, ctx, *, reason="Server lockdown"):
        locked = 0
        for channel in ctx.guild.text_channels:
            try:
                overwrite = channel.overwrites_for(ctx.guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
                locked += 1
            except Exception:
                pass
        await ctx.send(embed=make_embed(f"🔒 Locked **{locked}** channels.\nReason: {reason}", self.bot.error_color))

    # ─── SLOWMODE ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="slowmode", aliases=["sm"])
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        if seconds < 0 or seconds > 21600:
            return await ctx.send(embed=make_embed("❌ Slowmode must be between 0 and 21600 seconds.", self.bot.error_color))
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send(embed=make_embed(f"✅ Slowmode disabled in {ctx.channel.mention}.", self.bot.success_color))
        else:
            await ctx.send(embed=make_embed(f"✅ Slowmode set to **{seconds}s** in {ctx.channel.mention}.", self.bot.success_color))

    # ─── NICK ─────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="nick", aliases=["nickname"])
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, nickname: str = None):
        old = member.display_name
        await member.edit(nick=nickname)
        if nickname:
            await ctx.send(embed=make_embed(f"✅ Changed **{old}'s** nickname to **{nickname}**.", self.bot.success_color))
        else:
            await ctx.send(embed=make_embed(f"✅ Reset **{old}'s** nickname.", self.bot.success_color))

    # ─── ROLE MANAGEMENT ──────────────────────────────────────────────────────

    @commands.hybrid_command(name="addrole", aliases=["ar"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def addrole(self, ctx, member: discord.Member, role: discord.Role):
        if role in member.roles:
            return await ctx.send(embed=make_embed(f"❌ {member.mention} already has {role.mention}.", self.bot.error_color))
        await member.add_roles(role)
        await ctx.send(embed=make_embed(f"✅ Added {role.mention} to {member.mention}.", self.bot.success_color))

    @commands.hybrid_command(name="removerole", aliases=["rr"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def removerole(self, ctx, member: discord.Member, role: discord.Role):
        if role not in member.roles:
            return await ctx.send(embed=make_embed(f"❌ {member.mention} doesn't have {role.mention}.", self.bot.error_color))
        await member.remove_roles(role)
        await ctx.send(embed=make_embed(f"✅ Removed {role.mention} from {member.mention}.", self.bot.success_color))

    # ─── CHANNEL MANAGEMENT ───────────────────────────────────────────────────

    @commands.hybrid_command(name="nuke")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def nuke(self, ctx):
        channel = ctx.channel
        pos = channel.position
        new_channel = await channel.clone(reason=f"Nuked by {ctx.author}")
        await new_channel.edit(position=pos)
        await channel.delete(reason=f"Nuked by {ctx.author}")
        await new_channel.send(embed=make_embed(f"💥 Channel nuked by **{ctx.author}**.", self.bot.error_color))

    # ─── MODLOG ───────────────────────────────────────────────────────────────

    async def _log(self, guild, action, moderator, target, reason, extra=None):
        cfg = load_json("data/config.json")
        guild_id = str(guild.id)
        log_channel_id = cfg.get(guild_id, {}).get("mod_log_channel")
        if not log_channel_id:
            return
        channel = guild.get_channel(int(log_channel_id))
        if not channel:
            return
        colors = {
            "Ban": 0xED4245,
            "Kick": 0xFEE75C,
            "Mute": 0xEB459E,
            "Warn": 0xFEE75C,
            "Unban": 0x57F287,
        }
        embed = discord.Embed(
            title=f"🛡️ Moderation Action — {action}",
            color=colors.get(action, 0x5865F2),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Target", value=f"{target.mention} (`{target.id}`)", inline=True)
        embed.add_field(name="Moderator", value=f"{moderator.mention}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        if extra:
            embed.add_field(name="Extra", value=extra, inline=False)
        embed.set_footer(text=f"ID: {target.id}")
        await channel.send(embed=embed)

    @commands.hybrid_command(name="setmodlog")
    @commands.has_permissions(administrator=True)
    async def setmodlog(self, ctx, channel: discord.TextChannel):
        cfg = load_json("data/config.json")
        guild_id = str(ctx.guild.id)
        if guild_id not in cfg:
            cfg[guild_id] = {}
        cfg[guild_id]["mod_log_channel"] = str(channel.id)
        save_json("data/config.json", cfg)
        await ctx.send(embed=make_embed(f"✅ Mod log channel set to {channel.mention}.", self.bot.success_color))


# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def parse_time(time_str: str) -> int:
    """Parse a time string like '1d', '2h', '30m', '45s' to seconds."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    time_str = time_str.lower().strip()
    if time_str[-1] in units and time_str[:-1].isdigit():
        return int(time_str[:-1]) * units[time_str[-1]]
    return 0


async def setup(bot):
    await bot.add_cog(Moderation(bot))
