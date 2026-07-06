"""
Roles System - Reaction roles, mass roles, temp roles
"""

import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timezone, timedelta
from utils.helpers import make_embed, load_json, save_json

RR_FILE = "data/reaction_roles.json"


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─── REACTION ROLES ───────────────────────────────────────────────────────

    @commands.hybrid_command(name="reactionrole", aliases=["rr", "rrole"])
    @commands.has_permissions(manage_roles=True)
    async def reactionrole(self, ctx, message_id: int, emoji: str, role: discord.Role):
        """Add a reaction role to a message."""
        try:
            msg = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send(embed=make_embed("❌ Message not found in this channel.", self.bot.error_color))

        await msg.add_reaction(emoji)

        data = load_json(RR_FILE)
        guild_id = str(ctx.guild.id)
        msg_id = str(message_id)

        if guild_id not in data:
            data[guild_id] = {}
        if msg_id not in data[guild_id]:
            data[guild_id][msg_id] = {}

        data[guild_id][msg_id][emoji] = str(role.id)
        save_json(RR_FILE, data)

        await ctx.send(embed=make_embed(f"✅ Reaction role added!\n{emoji} → {role.mention}", self.bot.success_color))

    @commands.hybrid_command(name="rrremove")
    @commands.has_permissions(manage_roles=True)
    async def rrremove(self, ctx, message_id: int, emoji: str = None):
        """Remove reaction role(s) from a message."""
        data = load_json(RR_FILE)
        guild_id = str(ctx.guild.id)
        msg_id = str(message_id)

        if guild_id not in data or msg_id not in data[guild_id]:
            return await ctx.send(embed=make_embed("❌ No reaction roles for that message.", self.bot.error_color))

        if emoji:
            data[guild_id][msg_id].pop(emoji, None)
            if not data[guild_id][msg_id]:
                del data[guild_id][msg_id]
            save_json(RR_FILE, data)
            await ctx.send(embed=make_embed(f"✅ Removed reaction role for {emoji}.", self.bot.success_color))
        else:
            del data[guild_id][msg_id]
            save_json(RR_FILE, data)
            await ctx.send(embed=make_embed("✅ Removed all reaction roles for that message.", self.bot.success_color))

    @commands.hybrid_command(name="rrlist")
    @commands.has_permissions(manage_roles=True)
    async def rrlist(self, ctx):
        """List all reaction roles for this server."""
        data = load_json(RR_FILE)
        guild_id = str(ctx.guild.id)
        guild_data = data.get(guild_id, {})

        if not guild_data:
            return await ctx.send(embed=make_embed("No reaction roles configured.", 0x5865F2))

        embed = discord.Embed(title="🎭 Reaction Roles", color=0x5865F2)
        for msg_id, emojis in guild_data.items():
            lines = []
            for emoji, role_id in emojis.items():
                role = ctx.guild.get_role(int(role_id))
                lines.append(f"{emoji} → {role.mention if role else f'<deleted role {role_id}>'}")
            embed.add_field(
                name=f"Message ID: {msg_id}",
                value="\n".join(lines) or "Empty",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        await self._handle_reaction(payload, add=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        await self._handle_reaction(payload, add=False)

    async def _handle_reaction(self, payload: discord.RawReactionActionEvent, add: bool):
        data = load_json(RR_FILE)
        guild_id = str(payload.guild_id)
        msg_id = str(payload.message_id)
        emoji = str(payload.emoji)

        role_id = data.get(guild_id, {}).get(msg_id, {}).get(emoji)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        role = guild.get_role(int(role_id))
        if not role:
            return
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        try:
            if add:
                await member.add_roles(role, reason="Reaction role")
            else:
                await member.remove_roles(role, reason="Reaction role removed")
        except discord.Forbidden:
            pass

    # ─── PANEL REACTION ROLE ──────────────────────────────────────────────────

    @commands.hybrid_command(name="rrpanel")
    @commands.has_permissions(manage_roles=True)
    async def rrpanel(self, ctx, channel: discord.TextChannel = None, *, title: str = "🎭 Role Selection"):
        """Create an interactive reaction role panel via prompt."""
        channel = channel or ctx.channel
        await ctx.send(embed=make_embed(
            "I'll walk you through creating a reaction role panel.\n"
            "Enter pairs of `emoji role` (one per line), then send `done` when finished.\n"
            "Example:\n`🎮 @Gamer`\n`🎵 @Music`",
            0x5865F2
        ))

        pairs = {}
        for _ in range(20):
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=60)
            except asyncio.TimeoutError:
                break

            if msg.content.lower() == "done":
                break

            parts = msg.content.split()
            if len(parts) < 2:
                continue
            emoji = parts[0]
            role = None
            if msg.role_mentions:
                role = msg.role_mentions[0]
            else:
                try:
                    role = ctx.guild.get_role(int(parts[1]))
                except Exception:
                    pass
            if emoji and role:
                pairs[emoji] = role
                await msg.add_reaction("✅")

        if not pairs:
            return await ctx.send(embed=make_embed("❌ No valid pairs provided.", self.bot.error_color))

        embed = discord.Embed(
            title=title,
            description="React with an emoji below to get the corresponding role!\n\n" +
                        "\n".join(f"{e} → {r.mention}" for e, r in pairs.items()),
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Click an emoji to toggle your role")

        panel_msg = await channel.send(embed=embed)
        for emoji in pairs:
            try:
                await panel_msg.add_reaction(emoji)
            except Exception:
                pass

        data = load_json(RR_FILE)
        guild_id = str(ctx.guild.id)
        msg_id = str(panel_msg.id)
        if guild_id not in data:
            data[guild_id] = {}
        data[guild_id][msg_id] = {e: str(r.id) for e, r in pairs.items()}
        save_json(RR_FILE, data)

        await ctx.send(embed=make_embed(f"✅ Reaction role panel created in {channel.mention}!", self.bot.success_color))

    # ─── MASS ROLE ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="massrole")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def massrole(self, ctx, role: discord.Role, target: str = "humans"):
        """
        Add a role to all members.
        target: humans | bots | all
        """
        if target == "humans":
            members = [m for m in ctx.guild.members if not m.bot]
        elif target == "bots":
            members = [m for m in ctx.guild.members if m.bot]
        else:
            members = ctx.guild.members

        msg = await ctx.send(embed=make_embed(f"⏳ Adding {role.mention} to {len(members)} member(s)...", 0x5865F2))
        success, failed = 0, 0
        for member in members:
            try:
                if role not in member.roles:
                    await member.add_roles(role, reason=f"Mass role by {ctx.author}")
                    success += 1
                await asyncio.sleep(0.3)
            except Exception:
                failed += 1

        await msg.edit(embed=make_embed(
            f"✅ Mass role complete!\nAdded: **{success}** | Failed: **{failed}**",
            self.bot.success_color
        ))

    @commands.hybrid_command(name="massunrole")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def massunrole(self, ctx, role: discord.Role, target: str = "humans"):
        """Remove a role from all members."""
        if target == "humans":
            members = [m for m in ctx.guild.members if not m.bot and role in m.roles]
        elif target == "bots":
            members = [m for m in ctx.guild.members if m.bot and role in m.roles]
        else:
            members = [m for m in ctx.guild.members if role in m.roles]

        msg = await ctx.send(embed=make_embed(f"⏳ Removing {role.mention} from {len(members)} member(s)...", 0x5865F2))
        success, failed = 0, 0
        for member in members:
            try:
                await member.remove_roles(role, reason=f"Mass unrole by {ctx.author}")
                success += 1
                await asyncio.sleep(0.3)
            except Exception:
                failed += 1

        await msg.edit(embed=make_embed(
            f"✅ Mass unrole complete!\nRemoved: **{success}** | Failed: **{failed}**",
            self.bot.success_color
        ))

    # ─── TEMP ROLE ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="temprole")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def temprole(self, ctx, member: discord.Member, duration: str, role: discord.Role, *, reason: str = "Temp role"):
        """Give a member a role temporarily."""
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        duration_lower = duration.lower()
        if duration_lower[-1] in units and duration_lower[:-1].isdigit():
            seconds = int(duration_lower[:-1]) * units[duration_lower[-1]]
        else:
            return await ctx.send(embed=make_embed("❌ Invalid duration.", self.bot.error_color))

        await member.add_roles(role, reason=f"Temp role ({duration}): {reason}")
        await ctx.send(embed=make_embed(
            f"✅ Gave {member.mention} **{role.name}** for `{duration}`.\nReason: {reason}",
            self.bot.success_color
        ))
        await asyncio.sleep(seconds)
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Temp role expired")
        except Exception:
            pass

    # ─── ROLE INFO ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="rolecolor", aliases=["rc"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def rolecolor(self, ctx, role: discord.Role, color: str):
        """Change the color of a role."""
        try:
            color_int = int(color.replace("#", ""), 16)
            await role.edit(color=discord.Color(color_int))
            embed = discord.Embed(
                description=f"✅ Changed {role.mention} color to `{color}`",
                color=color_int
            )
            await ctx.send(embed=embed)
        except ValueError:
            await ctx.send(embed=make_embed("❌ Invalid color hex.", self.bot.error_color))

    @commands.hybrid_command(name="rolename")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def rolename(self, ctx, role: discord.Role, *, new_name: str):
        """Rename a role."""
        old_name = role.name
        await role.edit(name=new_name)
        await ctx.send(embed=make_embed(f"✅ Renamed `{old_name}` → `{new_name}`", self.bot.success_color))

    @commands.hybrid_command(name="createrole")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def createrole(self, ctx, *, name: str):
        """Create a new role."""
        role = await ctx.guild.create_role(name=name, reason=f"Created by {ctx.author}")
        await ctx.send(embed=make_embed(f"✅ Created role {role.mention}", self.bot.success_color))

    @commands.hybrid_command(name="delrole")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def delrole(self, ctx, role: discord.Role):
        """Delete a role."""
        name = role.name
        await role.delete(reason=f"Deleted by {ctx.author}")
        await ctx.send(embed=make_embed(f"✅ Deleted role `{name}`", self.bot.success_color))


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
