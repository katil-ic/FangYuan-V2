"""
Polls System - Interactive poll creation and management
"""

import discord
from discord.ext import commands
import asyncio
import re
from datetime import datetime, timezone, timedelta
from utils.helpers import make_embed, load_json, save_json

POLLS_FILE = "data/polls.json"

POLL_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
YES_NO_EMOJIS = {"✅": "Yes", "❌": "No"}


class PollResultView(discord.ui.View):
    def __init__(self, poll_data: dict):
        super().__init__(timeout=None)
        self.poll_data = poll_data

    @discord.ui.button(label="📊 Results", style=discord.ButtonStyle.secondary, custom_id="poll:results")
    async def show_results(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            channel = interaction.guild.get_channel(int(self.poll_data["channel_id"]))
            msg = await channel.fetch_message(int(self.poll_data["message_id"]))
        except Exception:
            return await interaction.response.send_message("❌ Poll message not found.", ephemeral=True)

        options = self.poll_data.get("options", [])
        emojis = POLL_EMOJIS[:len(options)]

        vote_counts = {}
        for reaction in msg.reactions:
            emoji = str(reaction.emoji)
            if emoji in emojis:
                vote_counts[emoji] = reaction.count - 1  # subtract bot's own reaction

        total = sum(vote_counts.values())
        lines = []
        for i, option in enumerate(options):
            e = emojis[i]
            count = vote_counts.get(e, 0)
            pct = (count / total * 100) if total > 0 else 0
            bar_len = int(pct / 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            lines.append(f"{e} **{option}**\n`{bar}` {count} votes ({pct:.1f}%)")

        embed = discord.Embed(
            title=f"📊 Poll Results: {self.poll_data.get('question', 'Poll')}",
            description="\n\n".join(lines) or "No votes yet.",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Total votes: {total}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Polls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="poll")
    @commands.has_permissions(manage_messages=True)
    async def poll(self, ctx, duration: str = None, *, question_and_options: str = None):
        """
        Create a poll with up to 10 options.
        Usage: !poll [duration] <Question | Option 1 | Option 2 | ...>
        Duration optional: 1h, 30m, 1d etc.
        Example: !poll 1h What's your favorite color? | Red | Blue | Green
        """
        if not question_and_options:
            return await ctx.send(embed=make_embed(
                "**Usage:** `!poll [duration] <Question | Opt1 | Opt2 | ...>`\n"
                "**Example:** `!poll 1h Favorite color? | Red | Blue | Green`\n"
                "Duration is optional. Max 10 options.",
                0x5865F2
            ))

        # Check if duration was given
        seconds = 0
        if duration:
            try:
                units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
                if duration[-1] in units and duration[:-1].isdigit():
                    seconds = int(duration[:-1]) * units[duration[-1]]
                else:
                    # Not a duration, treat as part of question
                    question_and_options = f"{duration} {question_and_options}"
                    duration = None
            except Exception:
                question_and_options = f"{duration} {question_and_options}"
                duration = None

        parts = [p.strip() for p in question_and_options.split("|")]
        question = parts[0]
        options = parts[1:]

        if not options:
            # Yes/No poll
            embed = discord.Embed(
                title="📊 Poll",
                description=f"**{question}**\n\n✅ Yes\n❌ No",
                color=0x5865F2,
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text=f"Poll by {ctx.author}" + (f" • Ends in {duration}" if duration else ""))
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
        elif len(options) > 10:
            return await ctx.send(embed=make_embed("❌ Maximum 10 options allowed.", self.bot.error_color))
        else:
            emojis = POLL_EMOJIS[:len(options)]
            option_lines = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options))
            ends_at = int((datetime.now(timezone.utc) + timedelta(seconds=seconds)).timestamp()) if seconds else None

            embed = discord.Embed(
                title="📊 Poll",
                description=f"**{question}**\n\n{option_lines}",
                color=0x5865F2,
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            footer_text = f"Poll by {ctx.author}"
            if ends_at:
                footer_text += f" • Ends: {datetime.fromtimestamp(ends_at).strftime('%b %d %H:%M UTC')}"
            embed.set_footer(text=footer_text)
            if ends_at:
                embed.add_field(name="⏱️ Ends", value=f"<t:{ends_at}:R>", inline=False)

            poll_data = {
                "question": question,
                "options": options,
                "channel_id": str(ctx.channel.id),
                "message_id": None,
                "author_id": str(ctx.author.id),
                "ends_at": ends_at,
                "ended": False
            }
            view = PollResultView(poll_data)
            msg = await ctx.send(embed=embed, view=view)
            poll_data["message_id"] = str(msg.id)

            # Save poll
            data = load_json(POLLS_FILE)
            guild_id = str(ctx.guild.id)
            if guild_id not in data:
                data[guild_id] = {}
            data[guild_id][str(msg.id)] = poll_data
            save_json(POLLS_FILE, data)

            for emoji in emojis:
                await msg.add_reaction(emoji)
                await asyncio.sleep(0.2)

            if seconds:
                self.bot.loop.create_task(self._auto_end_poll(ctx.guild.id, ctx.channel.id, msg.id, seconds, question, options))

        try:
            await ctx.message.delete()
        except Exception:
            pass

    async def _auto_end_poll(self, guild_id: int, channel_id: int, msg_id: int, seconds: int, question: str, options: list):
        await asyncio.sleep(seconds)
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            channel = guild.get_channel(channel_id)
            if not channel:
                return
            msg = await channel.fetch_message(msg_id)

            emojis = POLL_EMOJIS[:len(options)]
            vote_counts = {}
            for reaction in msg.reactions:
                emoji = str(reaction.emoji)
                if emoji in emojis:
                    vote_counts[emoji] = reaction.count - 1

            total = sum(vote_counts.values())
            winner_emoji = max(vote_counts, key=vote_counts.get) if vote_counts else None
            winner_idx = emojis.index(winner_emoji) if winner_emoji else None
            winner_option = options[winner_idx] if winner_idx is not None else "No winner"

            lines = []
            for i, option in enumerate(options):
                e = emojis[i]
                count = vote_counts.get(e, 0)
                pct = (count / total * 100) if total > 0 else 0
                bar_len = int(pct / 10)
                bar = "█" * bar_len + "░" * (10 - bar_len)
                lines.append(f"{e} **{option}**\n`{bar}` {count} votes ({pct:.1f}%)")

            embed = discord.Embed(
                title="📊 Poll Ended!",
                description=f"**{question}**\n\n" + "\n\n".join(lines),
                color=0x57F287,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="🏆 Winner", value=f"{winner_emoji} **{winner_option}**" if winner_emoji else "No votes", inline=False)
            embed.set_footer(text=f"Total votes: {total}")
            await msg.edit(embed=embed, view=None)

            # Update data
            data = load_json(POLLS_FILE)
            g_id = str(guild_id)
            if g_id in data and str(msg_id) in data[g_id]:
                data[g_id][str(msg_id)]["ended"] = True
                save_json(POLLS_FILE, data)
        except Exception:
            pass

    @commands.hybrid_command(name="quickpoll", aliases=["qp"])
    async def quickpoll(self, ctx, *, question: str):
        """Create a quick yes/no poll."""
        embed = discord.Embed(
            title="📊 Quick Poll",
            description=f"**{question}**",
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"React to vote!")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.hybrid_command(name="endpoll")
    @commands.has_permissions(manage_messages=True)
    async def endpoll(self, ctx, message_id: int):
        """Manually end a poll and show results."""
        try:
            msg = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send(embed=make_embed("❌ Message not found.", self.bot.error_color))

        data = load_json(POLLS_FILE)
        guild_id = str(ctx.guild.id)
        poll_data = data.get(guild_id, {}).get(str(message_id))

        if not poll_data:
            return await ctx.send(embed=make_embed("❌ No poll data for that message. It may not have been created with `!poll`.", self.bot.error_color))

        if poll_data.get("ended"):
            return await ctx.send(embed=make_embed("❌ That poll has already ended.", self.bot.error_color))

        options = poll_data.get("options", [])
        question = poll_data.get("question", "Poll")
        emojis = POLL_EMOJIS[:len(options)]

        vote_counts = {}
        for reaction in msg.reactions:
            emoji = str(reaction.emoji)
            if emoji in emojis:
                vote_counts[emoji] = reaction.count - 1

        total = sum(vote_counts.values())
        winner_emoji = max(vote_counts, key=vote_counts.get) if vote_counts else None
        winner_idx = emojis.index(winner_emoji) if winner_emoji in emojis else None
        winner_option = options[winner_idx] if winner_idx is not None else "No winner"

        lines = []
        for i, option in enumerate(options):
            e = emojis[i]
            count = vote_counts.get(e, 0)
            pct = (count / total * 100) if total > 0 else 0
            bar_len = int(pct / 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            lines.append(f"{e} **{option}**\n`{bar}` {count} votes ({pct:.1f}%)")

        embed = discord.Embed(
            title="📊 Poll Ended!",
            description=f"**{question}**\n\n" + "\n\n".join(lines),
            color=0x57F287,
            timestamp=datetime.utcnow()
        )
        if winner_emoji:
            embed.add_field(name="🏆 Winner", value=f"{winner_emoji} **{winner_option}**", inline=False)
        embed.set_footer(text=f"Total votes: {total} • Ended by {ctx.author}")
        await msg.edit(embed=embed, view=None)

        poll_data["ended"] = True
        data[guild_id][str(message_id)] = poll_data
        save_json(POLLS_FILE, data)

        await ctx.send(embed=make_embed(f"✅ Poll ended. Winner: **{winner_option}** ({vote_counts.get(winner_emoji, 0)} votes)", self.bot.success_color))

    @commands.hybrid_command(name="strawpoll")
    @commands.has_permissions(manage_messages=True)
    async def strawpoll(self, ctx, channel: discord.TextChannel = None, *, question_options: str = None):
        """Send a styled multi-option poll to a specific channel."""
        channel = channel or ctx.channel
        if not question_options:
            return await ctx.send(embed=make_embed("Usage: `!strawpoll [#channel] Question | Option1 | Option2 ...`", 0x5865F2))

        parts = [p.strip() for p in question_options.split("|")]
        question = parts[0]
        options = parts[1:] if len(parts) > 1 else []

        if not options:
            options = ["Yes", "No"]

        emojis = POLL_EMOJIS[:len(options)]
        option_lines = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options))

        embed = discord.Embed(
            title="🗳️ Straw Poll",
            color=0xFEE75C,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="❓ Question", value=f"**{question}**", inline=False)
        embed.add_field(name="Options", value=option_lines, inline=False)
        embed.set_footer(text=f"React to vote • Created by {ctx.author}")

        msg = await channel.send(embed=embed)
        for emoji in emojis:
            await msg.add_reaction(emoji)
            await asyncio.sleep(0.2)

        if channel != ctx.channel:
            await ctx.send(embed=make_embed(f"✅ Poll sent to {channel.mention}!", self.bot.success_color))
        try:
            await ctx.message.delete()
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Polls(bot))
