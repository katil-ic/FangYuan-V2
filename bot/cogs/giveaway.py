"""
Giveaway System - Full featured giveaway management
"""

import discord
from discord.ext import commands
import asyncio
import random
import re
from datetime import datetime, timezone, timedelta
from utils.helpers import make_embed, load_json, save_json

GA_FILE = "data/giveaways.json"

GIVEAWAY_EMOJI = "<a:ri_tada:1523620315325010092>"


def parse_time(time_str: str) -> int:
    """Parse e.g. 1d, 2h, 30m, 45s → seconds."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    time_str = time_str.lower().strip()
    total = 0
    pattern = r"(\d+)([smhdw])"
    for match in re.finditer(pattern, time_str):
        total += int(match.group(1)) * units[match.group(2)]
    return total if total else 0


def format_duration(seconds: int) -> str:
    d, r = divmod(int(seconds), 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s: parts.append(f"{s}s")
    return " ".join(parts) or "0s"


def build_giveaway_embed(prize: str, host: discord.Member, ends_at: int, winners: int,
                          entries: int, description: str = None, requirements: str = None, ended: bool = False) -> discord.Embed:
    color = 0xED4245 if ended else 0xFEE75C
    title = f"{'<a:rizz_rewards:1523620313689100320>' if ended else '<a:ri_tada:1523620315325010092>'} {'ENDED: ' if ended else ''}{prize}"

    embed = discord.Embed(title=title, color=color, timestamp=datetime.utcnow())

    if description:
        embed.description = description + "\n\n"
    else:
        embed.description = ""

    if not ended:
        embed.description += f"React with {GIVEAWAY_EMOJI} to enter!\n\n"

    embed.description += (
        f"> **Winners:** {winners}\n"
        f"> **Entries:** {entries}\n"
        f"> **Hosted by:** {host.mention}\n"
    )
    if requirements:
        embed.description += f"> **Requirements:** {requirements}\n"
    if not ended:
        embed.description += f"\n**Ends:** <t:{ends_at}:R> (<t:{ends_at}:F>)"
    else:
        embed.description += f"\n**Ended:** <t:{ends_at}:F>"

    embed.set_footer(text=f"FangYuan V2 Giveaways • {'Ended' if ended else 'Ends'}: {datetime.fromtimestamp(ends_at).strftime('%b %d, %Y %H:%M UTC')}")
    return embed


class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enter", emoji="<a:ri_tada:1523620315325010092>", style=discord.ButtonStyle.success, custom_id="giveaway:enter")
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_json(GA_FILE)
        guild_id = str(interaction.guild.id)
        msg_id = str(interaction.message.id)

        giveaway = data.get(guild_id, {}).get(msg_id)
        if not giveaway:
            return await interaction.response.send_message("<:Xieron_stolen_emoji_1774597520:1520895245733204039> This giveaway no longer exists.", ephemeral=True)
        if giveaway.get("ended"):
            return await interaction.response.send_message("<:Xieron_stolen_emoji_1774597520:1520895245733204039> This giveaway has already ended.", ephemeral=True)

        user_id = str(interaction.user.id)
        entries = giveaway.get("entries", [])

        if user_id in entries:
            entries.remove(user_id)
            data[guild_id][msg_id]["entries"] = entries
            save_json(GA_FILE, data)
            total = len(entries)
            # Update embed entry count
            try:
                embed = interaction.message.embeds[0]
                embed.description = re.sub(r"> \*\*Entries:\*\* \d+", f"> **Entries:** {total}", embed.description)
                await interaction.message.edit(embed=embed)
            except Exception:
                pass
            return await interaction.response.send_message("<:Xieron_stolen_emoji_1774597520:1520895245733204039> You've left the giveaway.", ephemeral=True)
        else:
            entries.append(user_id)
            data[guild_id][msg_id]["entries"] = entries
            save_json(GA_FILE, data)
            total = len(entries)
            # Update embed entry count
            try:
                embed = interaction.message.embeds[0]
                embed.description = re.sub(r"> \*\*Entries:\*\* \d+", f"> **Entries:** {total}", embed.description)
                await interaction.message.edit(embed=embed)
            except Exception:
                pass
            return await interaction.response.send_message(f"<a:tick:1523383850749792397> You've entered! Total entries: **{total}**", ephemeral=True)


class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(GiveawayView())
        self._task = None

    async def cog_load(self):
        self._task = self.bot.loop.create_task(self._giveaway_loop())

    async def cog_unload(self):
        if self._task:
            self._task.cancel()

    async def _giveaway_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                data = load_json(GA_FILE)
                now = int(datetime.now(timezone.utc).timestamp())
                for guild_id, giveaways in list(data.items()):
                    for msg_id, ga in list(giveaways.items()):
                        if ga.get("ended"):
                            continue
                        if ga.get("ends_at", 0) <= now:
                            guild = self.bot.get_guild(int(guild_id))
                            if guild:
                                await self._end_giveaway(guild, guild_id, msg_id, data)
            except Exception:
                pass
            await asyncio.sleep(10)

    async def _end_giveaway(self, guild: discord.Guild, guild_id: str, msg_id: str, data: dict):
        ga = data[guild_id][msg_id]
        channel = guild.get_channel(int(ga["channel_id"]))
        if not channel:
            return

        try:
            msg = await channel.fetch_message(int(msg_id))
        except Exception:
            data[guild_id][msg_id]["ended"] = True
            save_json(GA_FILE, data)
            return

        entries = ga.get("entries", [])
        winner_count = ga.get("winners", 1)
        prize = ga.get("prize", "Unknown Prize")
        host_id = ga.get("host_id")
        host = guild.get_member(int(host_id)) if host_id else None
        ends_at = ga.get("ends_at", int(datetime.now(timezone.utc).timestamp()))

        if not entries:
            winners = []
            winner_text = "No valid entries."
        else:
            valid_entries = []
            for uid in entries:
                member = guild.get_member(int(uid))
                if member:
                    valid_entries.append(uid)

            winners = random.sample(valid_entries, min(winner_count, len(valid_entries)))
            winner_text = " ".join(f"<@{w}>" for w in winners)

        # Update giveaway embed
        ended_embed = build_giveaway_embed(
            prize=prize,
            host=host or guild.me,
            ends_at=ends_at,
            winners=winner_count,
            entries=len(entries),
            ended=True
        )
        ended_embed.add_field(name="<a:rizz_rewards:1523620313689100320> Winners", value=winner_text, inline=False)

        await msg.edit(embed=ended_embed, view=None)

        if winners:
            await channel.send(
                content=" ".join(f"<@{w}>" for w in winners),
                embed=discord.Embed(
                    title="<a:ri_tada:1523620315325010092> Giveaway Ended!",
                    description=f"Congratulations {winner_text}!\nYou won **{prize}**! <a:ri_tada:1523620315325010092>\n\nContact {host.mention if host else 'the host'} to claim your prize.",
                    color=0x57F287,
                    timestamp=datetime.utcnow()
                )
            )
        else:
            await channel.send(embed=make_embed(f"<a:ri_tada:1523620315325010092> The **{prize}** giveaway ended with no valid entries.", 0xFEE75C))

        data[guild_id][msg_id]["ended"] = True
        data[guild_id][msg_id]["winner_ids"] = winners
        save_json(GA_FILE, data)

    # ─── COMMANDS ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="gstart", aliases=["gcreate", "giveaway"])
    @commands.has_permissions(manage_guild=True)
    async def gstart(self, ctx, duration: str, winners: str, channel: discord.TextChannel = None, *, prize: str):
        """
        Start a giveaway.
        Usage: !gstart <duration> <winners>w [#channel] <prize>
        Example: !gstart 1d 2w #giveaways Free Discord Nitro
        """
        channel = channel or ctx.channel
        seconds = parse_time(duration)
        if not seconds:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Invalid duration. Use e.g. `1d`, `2h`, `30m`.", self.bot.error_color))

        try:
            w_count = int(winners.rstrip("w"))
        except ValueError:
            w_count = 1

        ends_at = int((datetime.now(timezone.utc) + timedelta(seconds=seconds)).timestamp())

        embed = build_giveaway_embed(
            prize=prize,
            host=ctx.author,
            ends_at=ends_at,
            winners=w_count,
            entries=0
        )

        view = GiveawayView()
        msg = await channel.send(embed=embed, view=view)

        data = load_json(GA_FILE)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            data[guild_id] = {}
        data[guild_id][str(msg.id)] = {
            "channel_id": str(channel.id),
            "prize": prize,
            "winners": w_count,
            "duration": seconds,
            "ends_at": ends_at,
            "host_id": str(ctx.author.id),
            "entries": [],
            "ended": False,
            "created_at": int(datetime.now(timezone.utc).timestamp())
        }
        save_json(GA_FILE, data)

        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Giveaway started in {channel.mention}!\n[Jump to giveaway]({msg.jump_url})", self.bot.success_color), delete_after=10)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.hybrid_command(name="gend", aliases=["giveawayend"])
    @commands.has_permissions(manage_guild=True)
    async def gend(self, ctx, message_id: int = None):
        """End a giveaway early."""
        data = load_json(GA_FILE)
        guild_id = str(ctx.guild.id)

        if not message_id:
            # Find most recent active giveaway in this channel
            active = [(mid, ga) for mid, ga in data.get(guild_id, {}).items()
                      if ga["channel_id"] == str(ctx.channel.id) and not ga.get("ended")]
            if not active:
                return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> No active giveaway in this channel.", self.bot.error_color))
            message_id = int(active[-1][0])

        msg_id = str(message_id)
        if msg_id not in data.get(guild_id, {}):
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Giveaway not found.", self.bot.error_color))
        if data[guild_id][msg_id].get("ended"):
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> That giveaway has already ended.", self.bot.error_color))

        guild = ctx.guild
        await self._end_giveaway(guild, guild_id, msg_id, data)
        await ctx.send(embed=make_embed("<a:tick:1523383850749792397> Giveaway ended.", self.bot.success_color))

    @commands.hybrid_command(name="greroll", aliases=["giveawayreroll"])
    @commands.has_permissions(manage_guild=True)
    async def greroll(self, ctx, message_id: int = None, new_winners: int = None):
        """Reroll a completed giveaway."""
        data = load_json(GA_FILE)
        guild_id = str(ctx.guild.id)

        if not message_id:
            ended = [(mid, ga) for mid, ga in data.get(guild_id, {}).items() if ga.get("ended")]
            if not ended:
                return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> No ended giveaways found.", self.bot.error_color))
            message_id = int(ended[-1][0])

        msg_id = str(message_id)
        ga = data.get(guild_id, {}).get(msg_id)
        if not ga:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Giveaway not found.", self.bot.error_color))
        if not ga.get("ended"):
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Can only reroll ended giveaways.", self.bot.error_color))

        entries = ga.get("entries", [])
        w_count = new_winners or ga.get("winners", 1)
        valid = [uid for uid in entries if ctx.guild.get_member(int(uid))]

        if not valid:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> No valid entries to reroll from.", self.bot.error_color))

        winners = random.sample(valid, min(w_count, len(valid)))
        winner_text = " ".join(f"<@{w}>" for w in winners)

        embed = discord.Embed(
            title="🔄 Giveaway Rerolled!",
            description=f"New winner(s): {winner_text}\n\nPrize: **{ga['prize']}**",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        await ctx.send(content=winner_text, embed=embed)

    @commands.hybrid_command(name="glist", aliases=["giveaways"])
    @commands.has_permissions(manage_guild=True)
    async def glist(self, ctx):
        """List all active giveaways in this server."""
        data = load_json(GA_FILE)
        guild_id = str(ctx.guild.id)
        active = [(mid, ga) for mid, ga in data.get(guild_id, {}).items() if not ga.get("ended")]

        if not active:
            return await ctx.send(embed=make_embed("No active giveaways.", 0x5865F2))

        embed = discord.Embed(title="<a:ri_tada:1523620315325010092> Active Giveaways", color=0xFEE75C, timestamp=datetime.utcnow())
        for mid, ga in active:
            channel = ctx.guild.get_channel(int(ga["channel_id"]))
            ends_at = ga.get("ends_at", 0)
            embed.add_field(
                name=ga["prize"],
                value=(
                    f"Channel: {channel.mention if channel else 'Unknown'}\n"
                    f"Ends: <t:{ends_at}:R>\n"
                    f"Entries: {len(ga.get('entries', []))}\n"
                    f"Winners: {ga.get('winners', 1)}\n"
                    f"[Jump](https://discord.com/channels/{ctx.guild.id}/{ga['channel_id']}/{mid})"
                ),
                inline=True
            )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="gdelete")
    @commands.has_permissions(administrator=True)
    async def gdelete(self, ctx, message_id: int):
        """Delete a giveaway from the database."""
        data = load_json(GA_FILE)
        guild_id = str(ctx.guild.id)
        msg_id = str(message_id)
        if msg_id in data.get(guild_id, {}):
            del data[guild_id][msg_id]
            save_json(GA_FILE, data)
            await ctx.send(embed=make_embed("<a:tick:1523383850749792397> Giveaway deleted from database.", self.bot.success_color))
        else:
            await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Giveaway not found.", self.bot.error_color))

    @commands.hybrid_command(name="ginfo")
    @commands.has_permissions(manage_guild=True)
    async def ginfo(self, ctx, message_id: int):
        """Get info about a giveaway."""
        data = load_json(GA_FILE)
        guild_id = str(ctx.guild.id)
        ga = data.get(guild_id, {}).get(str(message_id))
        if not ga:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Giveaway not found.", self.bot.error_color))

        channel = ctx.guild.get_channel(int(ga["channel_id"]))
        host = ctx.guild.get_member(int(ga["host_id"])) if ga.get("host_id") else None
        ends_at = ga.get("ends_at", 0)
        embed = discord.Embed(
            title=f"<a:ri_tada:1523620315325010092> Giveaway Info: {ga['prize']}",
            color=0xFEE75C if not ga.get("ended") else 0x5865F2
        )
        embed.add_field(name="Status", value="Ended <a:tick:1523383850749792397>" if ga.get("ended") else "Active <a:ri_tada:1523620315325010092>", inline=True)
        embed.add_field(name="Channel", value=channel.mention if channel else "Unknown", inline=True)
        embed.add_field(name="Host", value=host.mention if host else "Unknown", inline=True)
        embed.add_field(name="Winners", value=str(ga.get("winners", 1)), inline=True)
        embed.add_field(name="Entries", value=str(len(ga.get("entries", []))), inline=True)
        embed.add_field(name="Ends At", value=f"<t:{ends_at}:F>", inline=True)
        if ga.get("winner_ids"):
            winner_text = " ".join(f"<@{w}>" for w in ga["winner_ids"])
            embed.add_field(name="<a:rizz_rewards:1523620313689100320> Winners", value=winner_text, inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Giveaway(bot))
