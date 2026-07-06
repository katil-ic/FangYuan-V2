"""
Welcome System - Custom welcome/leave messages with embeds
"""

import discord
from discord.ext import commands
from datetime import datetime
from utils.helpers import make_embed, load_json, save_json

WELCOME_FILE = "data/welcome.json"


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = load_json(WELCOME_FILE)
        guild_id = str(member.guild.id)
        g_cfg = cfg.get(guild_id, {})

        # ── Welcome message ──────────────────────────────────────────────────
        w_cfg = g_cfg.get("welcome", {})
        if w_cfg.get("enabled") and w_cfg.get("channel_id"):
            channel = member.guild.get_channel(int(w_cfg["channel_id"]))
            if channel:
                msg = w_cfg.get("message", "").replace(
                    "{user}", member.mention
                ).replace(
                    "{username}", str(member)
                ).replace(
                    "{server}", member.guild.name
                ).replace(
                    "{count}", str(member.guild.member_count)
                )

                embed = discord.Embed(
                    title=w_cfg.get("title", f"Welcome to {member.guild.name}!"),
                    description=msg or f"Welcome {member.mention} to **{member.guild.name}**! <a:ri_tada:1523620315325010092>\nYou are member **#{member.guild.member_count}**.",
                    color=int(w_cfg.get("color", "0x57F287"), 16) if isinstance(w_cfg.get("color"), str) else w_cfg.get("color", 0x57F287),
                    timestamp=datetime.utcnow()
                )
                if w_cfg.get("show_avatar", True):
                    embed.set_thumbnail(url=member.display_avatar.url)
                if w_cfg.get("show_banner") and member.guild.banner:
                    embed.set_image(url=member.guild.banner.url)
                embed.set_footer(text=w_cfg.get("footer", f"{member.guild.name} • FangYuan V2"))

                content = None
                if w_cfg.get("ping_user"):
                    content = member.mention
                await channel.send(content=content, embed=embed)

        # ── Auto-roles ────────────────────────────────────────────────────────
        autoroles = g_cfg.get("autoroles", [])
        for role_id in autoroles:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role on join")
                except Exception:
                    pass

        # ── DM welcome ───────────────────────────────────────────────────────
        dm_cfg = g_cfg.get("dm_welcome", {})
        if dm_cfg.get("enabled"):
            dm_msg = dm_cfg.get("message", f"Welcome to **{member.guild.name}**!")
            dm_msg = dm_msg.replace("{user}", str(member)).replace("{server}", member.guild.name)
            try:
                embed = discord.Embed(description=dm_msg, color=0x5865F2, timestamp=datetime.utcnow())
                if dm_cfg.get("title"):
                    embed.title = dm_cfg["title"]
                await member.send(embed=embed)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        cfg = load_json(WELCOME_FILE)
        guild_id = str(member.guild.id)
        l_cfg = cfg.get(guild_id, {}).get("leave", {})

        if not l_cfg.get("enabled") or not l_cfg.get("channel_id"):
            return

        channel = member.guild.get_channel(int(l_cfg["channel_id"]))
        if not channel:
            return

        msg = l_cfg.get("message", "").replace(
            "{user}", str(member)
        ).replace(
            "{username}", str(member)
        ).replace(
            "{server}", member.guild.name
        ).replace(
            "{count}", str(member.guild.member_count)
        )

        embed = discord.Embed(
            title=l_cfg.get("title", f"Goodbye from {member.guild.name}"),
            description=msg or f"**{member}** has left the server. <:waves_roleicon_Jo1nTrX:1480906869089374361>",
            color=int(l_cfg.get("color", "0xED4245"), 16) if isinstance(l_cfg.get("color"), str) else l_cfg.get("color", 0xED4245),
            timestamp=datetime.utcnow()
        )
        if l_cfg.get("show_avatar", True):
            embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=l_cfg.get("footer", f"We now have {member.guild.member_count} members."))
        await channel.send(embed=embed)

    # ─── SETUP COMMANDS ───────────────────────────────────────────────────────

    @commands.hybrid_group(name="welcome", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def welcome_group(self, ctx):
        cfg = load_json(WELCOME_FILE)
        g_cfg = cfg.get(str(ctx.guild.id), {})
        w_cfg = g_cfg.get("welcome", {})
        embed = discord.Embed(title="<a:ri_tada:1523620315325010092> Welcome System", color=0x5865F2)
        embed.add_field(name="Status", value="<a:tick:1523383850749792397> Enabled" if w_cfg.get("enabled") else "<:Xieron_stolen_emoji_1774597520:1520895245733204039> Disabled", inline=True)
        channel_id = w_cfg.get("channel_id")
        channel = ctx.guild.get_channel(int(channel_id)) if channel_id else None
        embed.add_field(name="Channel", value=channel.mention if channel else "Not set", inline=True)
        embed.add_field(name="Ping User", value="Yes" if w_cfg.get("ping_user") else "No", inline=True)
        embed.add_field(
            name="Commands",
            value=(
                "`!welcome setchannel #channel` — Set welcome channel\n"
                "`!welcome setmessage <text>` — Set message (use {user}, {server}, {count})\n"
                "`!welcome settitle <text>` — Set embed title\n"
                "`!welcome enable/disable` — Toggle\n"
                "`!welcome ping on/off` — Toggle user ping\n"
                "`!welcome test` — Send test message\n"
                "`!leave setchannel/setmessage/enable/disable` — Leave settings\n"
                "`!autorole add/remove @role` — Auto-roles on join\n"
                "`!dmwelcome set/enable/disable` — DM welcome messages"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @welcome_group.command(name="setchannel")
    @commands.has_permissions(manage_guild=True)
    async def welcome_setchannel(self, ctx, channel: discord.TextChannel):
        self._update(str(ctx.guild.id), "welcome", {"channel_id": str(channel.id)})
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Welcome channel set to {channel.mention}.", self.bot.success_color))

    @welcome_group.command(name="setmessage")
    @commands.has_permissions(manage_guild=True)
    async def welcome_setmessage(self, ctx, *, message: str):
        self._update(str(ctx.guild.id), "welcome", {"message": message})
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Welcome message updated.\n> {message}", self.bot.success_color))

    @welcome_group.command(name="settitle")
    @commands.has_permissions(manage_guild=True)
    async def welcome_settitle(self, ctx, *, title: str):
        self._update(str(ctx.guild.id), "welcome", {"title": title})
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Welcome title set to: **{title}**", self.bot.success_color))

    @welcome_group.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    async def welcome_enable(self, ctx):
        self._update(str(ctx.guild.id), "welcome", {"enabled": True})
        await ctx.send(embed=make_embed("<a:tick:1523383850749792397> Welcome system enabled.", self.bot.success_color))

    @welcome_group.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    async def welcome_disable(self, ctx):
        self._update(str(ctx.guild.id), "welcome", {"enabled": False})
        await ctx.send(embed=make_embed("<a:tick:1523383850749792397> Welcome system disabled.", self.bot.success_color))

    @welcome_group.command(name="ping")
    @commands.has_permissions(manage_guild=True)
    async def welcome_ping(self, ctx, toggle: str):
        val = toggle.lower() in ("on", "yes", "true", "enable")
        self._update(str(ctx.guild.id), "welcome", {"ping_user": val})
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> User ping {'enabled' if val else 'disabled'}.", self.bot.success_color))

    @welcome_group.command(name="test")
    @commands.has_permissions(manage_guild=True)
    async def welcome_test(self, ctx):
        await self.on_member_join(ctx.author)
        await ctx.send(embed=make_embed("<a:tick:1523383850749792397> Sent test welcome message.", self.bot.success_color))

    @welcome_group.command(name="setcolor")
    @commands.has_permissions(manage_guild=True)
    async def welcome_setcolor(self, ctx, color: str):
        try:
            int(color.replace("#", "0x"), 16)
        except ValueError:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Invalid color. Use hex like `#57F287`.", self.bot.error_color))
        self._update(str(ctx.guild.id), "welcome", {"color": color.replace("#", "0x")})
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Welcome color set to `{color}`.", self.bot.success_color))

    # ─── LEAVE ────────────────────────────────────────────────────────────────

    @commands.hybrid_group(name="leave", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def leave_group(self, ctx):
        await ctx.send(embed=make_embed("Use subcommands: `setchannel`, `setmessage`, `settitle`, `enable`, `disable`, `test`", 0x5865F2))

    @leave_group.command(name="setchannel")
    @commands.has_permissions(manage_guild=True)
    async def leave_setchannel(self, ctx, channel: discord.TextChannel):
        self._update(str(ctx.guild.id), "leave", {"channel_id": str(channel.id)})
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Leave channel set to {channel.mention}.", self.bot.success_color))

    @leave_group.command(name="setmessage")
    @commands.has_permissions(manage_guild=True)
    async def leave_setmessage(self, ctx, *, message: str):
        self._update(str(ctx.guild.id), "leave", {"message": message})
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Leave message updated.", self.bot.success_color))

    @leave_group.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    async def leave_enable(self, ctx):
        self._update(str(ctx.guild.id), "leave", {"enabled": True})
        await ctx.send(embed=make_embed("<a:tick:1523383850749792397> Leave system enabled.", self.bot.success_color))

    @leave_group.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    async def leave_disable(self, ctx):
        self._update(str(ctx.guild.id), "leave", {"enabled": False})
        await ctx.send(embed=make_embed("<a:tick:1523383850749792397> Leave system disabled.", self.bot.success_color))

    @leave_group.command(name="test")
    @commands.has_permissions(manage_guild=True)
    async def leave_test(self, ctx):
        await self.on_member_remove(ctx.author)
        await ctx.send(embed=make_embed("<a:tick:1523383850749792397> Sent test leave message.", self.bot.success_color))

    # ─── AUTO-ROLE ────────────────────────────────────────────────────────────

    @commands.hybrid_group(name="autorole", invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def autorole_group(self, ctx):
        cfg = load_json(WELCOME_FILE)
        guild_id = str(ctx.guild.id)
        roles = cfg.get(guild_id, {}).get("autoroles", [])
        if not roles:
            return await ctx.send(embed=make_embed("No auto-roles configured. Use `!autorole add @role`.", 0x5865F2))
        role_mentions = [ctx.guild.get_role(int(r)).mention for r in roles if ctx.guild.get_role(int(r))]
        embed = discord.Embed(title="<:ownerinfo:1523725199457910884> Auto-Roles", description="\n".join(role_mentions) or "None", color=0x5865F2)
        await ctx.send(embed=embed)

    @autorole_group.command(name="add")
    @commands.has_permissions(manage_roles=True)
    async def autorole_add(self, ctx, role: discord.Role):
        cfg = load_json(WELCOME_FILE)
        guild_id = str(ctx.guild.id)
        if guild_id not in cfg:
            cfg[guild_id] = {}
        if "autoroles" not in cfg[guild_id]:
            cfg[guild_id]["autoroles"] = []
        if str(role.id) not in cfg[guild_id]["autoroles"]:
            cfg[guild_id]["autoroles"].append(str(role.id))
            save_json(WELCOME_FILE, cfg)
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Added {role.mention} to auto-roles.", self.bot.success_color))

    @autorole_group.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    async def autorole_remove(self, ctx, role: discord.Role):
        cfg = load_json(WELCOME_FILE)
        guild_id = str(ctx.guild.id)
        roles = cfg.get(guild_id, {}).get("autoroles", [])
        if str(role.id) in roles:
            roles.remove(str(role.id))
            cfg[guild_id]["autoroles"] = roles
            save_json(WELCOME_FILE, cfg)
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Removed {role.mention} from auto-roles.", self.bot.success_color))

    # ─── DM WELCOME ───────────────────────────────────────────────────────────

    @commands.hybrid_group(name="dmwelcome", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def dmwelcome_group(self, ctx):
        await ctx.send(embed=make_embed("Use: `!dmwelcome set <message>`, `!dmwelcome enable`, `!dmwelcome disable`", 0x5865F2))

    @dmwelcome_group.command(name="set")
    @commands.has_permissions(manage_guild=True)
    async def dmwelcome_set(self, ctx, *, message: str):
        self._update(str(ctx.guild.id), "dm_welcome", {"message": message, "enabled": True})
        await ctx.send(embed=make_embed("<a:tick:1523383850749792397> DM welcome message set.", self.bot.success_color))

    @dmwelcome_group.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    async def dmwelcome_enable(self, ctx):
        self._update(str(ctx.guild.id), "dm_welcome", {"enabled": True})
        await ctx.send(embed=make_embed("<a:tick:1523383850749792397> DM welcome enabled.", self.bot.success_color))

    @dmwelcome_group.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    async def dmwelcome_disable(self, ctx):
        self._update(str(ctx.guild.id), "dm_welcome", {"enabled": False})
        await ctx.send(embed=make_embed("<a:tick:1523383850749792397> DM welcome disabled.", self.bot.success_color))

    # ─── HELPERS ──────────────────────────────────────────────────────────────

    def _update(self, guild_id, section, data):
        cfg = load_json(WELCOME_FILE)
        if guild_id not in cfg:
            cfg[guild_id] = {}
        if section not in cfg[guild_id]:
            cfg[guild_id][section] = {}
        cfg[guild_id][section].update(data)
        save_json(WELCOME_FILE, cfg)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
