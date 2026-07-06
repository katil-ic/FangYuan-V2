"""
Info Commands - Server, user, role, bot info
"""

import discord
from discord.ext import commands
from datetime import datetime, timezone
from utils.helpers import make_embed


def format_date(dt: datetime) -> str:
    return f"<t:{int(dt.timestamp())}:F> (<t:{int(dt.timestamp())}:R>)"


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="serverinfo", aliases=["si", "guildinfo"])
    async def serverinfo(self, ctx):
        """Show detailed server information."""
        g = ctx.guild
        await g.fetch_channels()

        text_channels = len(g.text_channels)
        voice_channels = len(g.voice_channels)
        categories = len(g.categories)
        roles = len(g.roles) - 1  # exclude @everyone
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots

        online = sum(1 for m in g.members if m.status == discord.Status.online)
        idle = sum(1 for m in g.members if m.status == discord.Status.idle)
        dnd = sum(1 for m in g.members if m.status == discord.Status.dnd)
        offline = sum(1 for m in g.members if m.status == discord.Status.offline)

        embed = discord.Embed(
            title=f"<a:Poll:1523725207846781071> {g.name}",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        if g.banner:
            embed.set_image(url=g.banner.with_size(1024).url)

        embed.add_field(name="<:ownerinfo:1523725199457910884> Server ID", value=str(g.id), inline=True)
        embed.add_field(name="<:owner:1523383841295827084> Owner", value=g.owner.mention if g.owner else "Unknown", inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Created", value=format_date(g.created_at), inline=False)
        embed.add_field(
            name=f"<:strangerz_girl_staff:1523386969101697174> Members ({g.member_count})",
            value=f"<:strangerz_girl_staff:1523386969101697174> Humans: {humans}\n<:ownerinfo:1523725199457910884> Bots: {bots}\n<a:online:1523383854226870423> Online: {online}\n<:ownerinfo:1523725199457910884> Idle: {idle}\n<:ownerinfo:1523725199457910884> DND: {dnd}\n<:ownerinfo:1523725199457910884> Offline: {offline}",
            inline=True
        )
        embed.add_field(
            name="<:ownerinfo:1523725199457910884> Channels",
            value=f"<:ownerinfo:1523725199457910884> Text: {text_channels}\n<:ownerinfo:1523725199457910884> Voice: {voice_channels}\n<:ownerinfo:1523725199457910884> Categories: {categories}",
            inline=True
        )
        embed.add_field(
            name="<:ownerinfo:1523725199457910884> Server Info",
            value=(
                f"<:ownerinfo:1523725199457910884> Region: {str(g.preferred_locale)}\n"
                f"<:ownerinfo:1523725199457910884> Verification: {g.verification_level.name.title()}\n"
                f"<:ownerinfo:1523725199457910884> Boost Level: {g.premium_tier}\n"
                f"<a:rizz_blacky_hearts:1523386407651905769> Boosts: {g.premium_subscription_count}\n"
                f"<:ownerinfo:1523725199457910884> Roles: {roles}"
            ),
            inline=True
        )

        features = [f.replace("_", " ").title() for f in g.features[:8]] if g.features else []
        if features:
            embed.add_field(name="<:Star2:1520896622932791296> Features", value=", ".join(features), inline=False)

        embed.set_footer(text=f"FangYuan V2 • Shard {ctx.guild.shard_id if ctx.guild.shard_id is not None else 0}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="userinfo", aliases=["ui", "whois", "user"])
    async def userinfo(self, ctx, member: discord.Member = None):
        """Show detailed user information."""
        member = member or ctx.author
        roles = [r.mention for r in reversed(member.roles) if r != ctx.guild.default_role]

        status_icons = {
            discord.Status.online: "<a:online:1523383854226870423>",
            discord.Status.idle: "<:ownerinfo:1523725199457910884>",
            discord.Status.dnd: "<:ownerinfo:1523725199457910884>",
            discord.Status.offline: "<:ownerinfo:1523725199457910884>"
        }
        status_icon = status_icons.get(member.status, "<:ownerinfo:1523725199457910884>")

        badges = []
        flags = member.public_flags
        if flags.staff: badges.append("<:strangerz_girl_staff:1523386969101697174>‍<:ownerinfo:1523725199457910884> Discord Staff")
        if flags.partner: badges.append("<:ownerinfo:1523725199457910884> Partner")
        if flags.bug_hunter: badges.append("<:ownerinfo:1523725199457910884> Bug Hunter")
        if flags.early_supporter: badges.append("⭐ Early Supporter")
        if flags.verified_bot_developer: badges.append("<a:Mod:1520895258118983743> Bot Dev")
        if flags.hypesquad_balance: badges.append("<:Moderator:1520896609431457852> HypeSquad Balance")
        if flags.hypesquad_bravery: badges.append("<:ownerinfo:1523725199457910884> HypeSquad Bravery")
        if flags.hypesquad_brilliance: badges.append("<:ownerinfo:1523725199457910884> HypeSquad Brilliance")
        if member.bot: badges.append("<:ownerinfo:1523725199457910884> Bot")
        if member.premium_since: badges.append("<a:rizz_blacky_hearts:1523386407651905769> Nitro Booster")

        embed = discord.Embed(
            title=f"<:strangerz_girl_staff:1523386969101697174> {member}",
            color=member.color.value if member.color.value else 0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="<:ownerinfo:1523725199457910884> User ID", value=str(member.id), inline=True)
        embed.add_field(name="<:rank:1523386967511793824> Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name=f"{status_icon} Status", value=member.status.name.title(), inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Account Created", value=format_date(member.created_at), inline=False)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Joined Server", value=format_date(member.joined_at) if member.joined_at else "Unknown", inline=False)

        if member.premium_since:
            embed.add_field(name="<a:rizz_blacky_hearts:1523386407651905769> Boosting Since", value=format_date(member.premium_since), inline=False)

        if badges:
            embed.add_field(name="<a:rizz_rewards:1523620313689100320> Badges", value=" | ".join(badges), inline=False)

        if roles:
            roles_text = " ".join(roles[:20])
            if len(roles) > 20:
                roles_text += f" +{len(roles)-20} more"
            embed.add_field(name=f"<:ownerinfo:1523725199457910884> Roles ({len(roles)})", value=roles_text, inline=False)

        # Top role
        top_role = member.top_role
        if top_role != ctx.guild.default_role:
            embed.add_field(name="⭐ Top Role", value=top_role.mention, inline=True)

        # Activity
        if member.activity:
            act = member.activity
            act_text = ""
            if isinstance(act, discord.Game):
                act_text = f"<:ownerinfo:1523725199457910884> Playing {act.name}"
            elif isinstance(act, discord.Spotify):
                act_text = f"<:ownerinfo:1523725199457910884> {act.title} by {act.artist}"
            elif isinstance(act, discord.Streaming):
                act_text = f"<:ownerinfo:1523725199457910884> Streaming {act.name}"
            elif isinstance(act, discord.CustomActivity) and act.name:
                act_text = f"<:ownerinfo:1523725199457910884> {act.name}"
            if act_text:
                embed.add_field(name="<:ownerinfo:1523725199457910884> Activity", value=act_text, inline=False)

        embed.set_footer(text="FangYuan V2")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", aliases=["av", "pfp"])
    async def avatar(self, ctx, member: discord.Member = None):
        """Show a user's avatar in full size."""
        member = member or ctx.author
        embed = discord.Embed(title=f"<:ownerinfo:1523725199457910884> {member.display_name}'s Avatar", color=0x5865F2)
        embed.set_image(url=member.display_avatar.with_size(1024).url)
        embed.add_field(
            name="Links",
            value=f"[PNG]({member.display_avatar.replace(format='png', size=1024).url}) | "
                  f"[WEBP]({member.display_avatar.replace(format='webp', size=1024).url}) | "
                  f"[JPG]({member.display_avatar.replace(format='jpg', size=1024).url})",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="banner")
    async def banner(self, ctx, member: discord.User = None):
        """Show a user's profile banner."""
        member = member or ctx.author
        fetched = await self.bot.fetch_user(member.id)
        if not fetched.banner:
            return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> **{member}** doesn't have a banner.", self.bot.error_color))
        embed = discord.Embed(title=f"<:ownerinfo:1523725199457910884> {member}'s Banner", color=0x5865F2)
        embed.set_image(url=fetched.banner.with_size(1024).url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="roleinfo", aliases=["ri"])
    async def roleinfo(self, ctx, *, role: discord.Role):
        """Show detailed role information."""
        perms = [p.replace("_", " ").title() for p, v in role.permissions if v]
        key_perms = [p for p in perms if p in (
            "Administrator", "Manage Guild", "Manage Roles", "Ban Members",
            "Kick Members", "Manage Messages", "Manage Channels", "Mention Everyone"
        )]

        embed = discord.Embed(
            title=f"<:ownerinfo:1523725199457910884> Role: {role.name}",
            color=role.color.value if role.color.value else 0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="<:ownerinfo:1523725199457910884> ID", value=str(role.id), inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Color", value=f"#{role.color.value:06X}", inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Position", value=str(role.position), inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Created", value=format_date(role.created_at), inline=False)
        embed.add_field(name="<:strangerz_girl_staff:1523386969101697174> Members", value=str(len(role.members)), inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Bot Role", value="Yes" if role.is_bot_managed() else "No", inline=True)
        embed.add_field(name="<a:rizz_blacky_hearts:1523386407651905769> Booster Role", value="Yes" if role.is_premium_subscriber() else "No", inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Hoisted", value="Yes" if role.hoist else "No", inline=True)
        if key_perms:
            embed.add_field(name="<:ownerinfo:1523725199457910884> Key Permissions", value=", ".join(key_perms), inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="channelinfo", aliases=["ci"])
    async def channelinfo(self, ctx, channel: discord.TextChannel = None):
        """Show detailed channel information."""
        channel = channel or ctx.channel
        embed = discord.Embed(
            title=f"<:ownerinfo:1523725199457910884> Channel: #{channel.name}",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="<:ownerinfo:1523725199457910884> ID", value=str(channel.id), inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Category", value=channel.category.name if channel.category else "None", inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Position", value=str(channel.position), inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Created", value=format_date(channel.created_at), inline=False)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Slowmode", value=f"{channel.slowmode_delay}s" if channel.slowmode_delay else "Off", inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> NSFW", value="Yes" if channel.nsfw else "No", inline=True)
        if channel.topic:
            embed.add_field(name="<:ownerinfo:1523725199457910884> Topic", value=channel.topic[:1024], inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="botinfo", aliases=["bi", "about"])
    async def botinfo(self, ctx):
        """Show information about FangYuan V2."""
        import platform
        import psutil
        import time
        import os

        process = psutil.Process(os.getpid())
        memory = process.memory_info().rss / 1024 / 1024
        cpu = psutil.cpu_percent(interval=1)

        uptime = datetime.now(timezone.utc) - self.bot.start_time
        d, r = divmod(int(uptime.total_seconds()), 86400)
        h, r = divmod(r, 3600)
        m, s = divmod(r, 60)
        uptime_str = f"{d}d {h}h {m}m {s}s"

        embed = discord.Embed(
            title="<:ownerinfo:1523725199457910884> FangYuan V2",
            description="A powerful all-in-one Discord bot built for large public servers.",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="<:strangerz_girl_staff:1523386969101697174> Owner", value=f"<@{list(self.bot.owner_ids)[0]}>" if self.bot.owner_ids else "Unknown", inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="<:strangerz_girl_staff:1523386969101697174> Users", value=f"{sum(g.member_count for g in self.bot.guilds):,}", inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Commands", value=str(len(list(self.bot.commands))), inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Uptime", value=uptime_str, inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Python", value=platform.python_version(), inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> Memory", value=f"{memory:.1f} MB", inline=True)
        embed.add_field(name="<:ownerinfo:1523725199457910884> CPU", value=f"{cpu:.1f}%", inline=True)
        embed.set_footer(text="FangYuan V2 • All-in-One Discord Bot")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="permissions", aliases=["perms"])
    async def permissions(self, ctx, member: discord.Member = None, channel: discord.TextChannel = None):
        """Show a member's permissions."""
        member = member or ctx.author
        channel = channel or ctx.channel
        perms = channel.permissions_for(member)
        allowed = [f"<a:tick:1523383850749792397> {p.replace('_', ' ').title()}" for p, v in perms if v]
        denied = [f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> {p.replace('_', ' ').title()}" for p, v in perms if not v]

        embed = discord.Embed(
            title=f"<:ownerinfo:1523725199457910884> Permissions for {member} in #{channel.name}",
            color=member.color.value or 0x5865F2
        )
        embed.add_field(name="Allowed", value="\n".join(allowed[:20]) or "None", inline=True)
        embed.add_field(name="Denied", value="\n".join(denied[:20]) or "None", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="emojis", aliases=["emojilist"])
    async def emojis(self, ctx):
        """List all server emojis."""
        emojis = ctx.guild.emojis
        if not emojis:
            return await ctx.send(embed=make_embed("No custom emojis in this server.", 0x5865F2))

        pages = []
        per_page = 30
        emoji_list = list(emojis)
        for i in range(0, len(emoji_list), per_page):
            chunk = emoji_list[i:i+per_page]
            pages.append(" ".join(str(e) for e in chunk))

        embed = discord.Embed(
            title=f"<:xD:1520896591542878219> Server Emojis ({len(emojis)})",
            description=pages[0] if pages else "None",
            color=0x5865F2
        )
        embed.set_footer(text=f"Static: {sum(1 for e in emojis if not e.animated)} | Animated: {sum(1 for e in emojis if e.animated)}")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Info(bot))
