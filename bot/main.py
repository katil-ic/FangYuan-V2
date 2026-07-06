"""
FangYuan V2 - All-in-One Discord Bot
"""

import discord
from discord.ext import commands
import asyncio
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("fangyuan.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FangYuan")

COGS = [
    "cogs.moderation",
    "cogs.tickets",
    "cogs.welcome",
    "cogs.embeds",
    "cogs.autoresponder",
    "cogs.announcements",
    "cogs.crypto",
    "cogs.giveaway",
    "cogs.utility",
    "cogs.roles",
    "cogs.polls",
    "cogs.info",
]


def get_prefix(bot, message):
    prefix = os.getenv("PREFIX", "!")
    return commands.when_mentioned_or(prefix)(bot, message)


class FangYuan(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_ids=set(
                int(i) for i in os.getenv("OWNER_IDS", "").split(",") if i.strip().isdigit()
            ),
        )
        self.start_time = datetime.utcnow()
        self.color = 0x2B2D31  # default embed color
        self.success_color = 0x57F287
        self.error_color = 0xED4245
        self.warning_color = 0xFEE75C
        self.info_color = 0x5865F2

    async def setup_hook(self):
        logger.info("Loading cogs...")
        for cog in COGS:
            try:
                await self.load_extension(cog)
                logger.info(f"  ✓ Loaded {cog}")
            except Exception as e:
                logger.error(f"  ✗ Failed to load {cog}: {e}")

        # Sync slash commands
        logger.info("Syncing application commands...")
        try:
            synced = await self.tree.sync()
            logger.info(f"  ✓ Synced {len(synced)} command(s) globally")
        except Exception as e:
            logger.error(f"  ✗ Sync failed: {e}")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Serving {len(self.guilds)} guild(s)")
        prefix = os.getenv("PREFIX", "!")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | {prefix}help / /help"
            ),
            status=discord.Status.online
        )

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description=f"❌ You don't have permission to use this command.",
                color=self.error_color
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        if isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description=f"❌ I'm missing permissions: `{', '.join(error.missing_permissions)}`",
                color=self.error_color
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        if isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                description="❌ Member not found.",
                color=self.error_color
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                description=f"❌ Missing required argument: `{error.param.name}`",
                color=self.error_color
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                description=f"⏳ Command on cooldown. Try again in `{error.retry_after:.1f}s`",
                color=self.warning_color
            )
            await ctx.send(embed=embed, delete_after=5)
            return
        logger.error(f"Unhandled command error in '{ctx.command}': {error}", exc_info=error)

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)


async def main():
    token = os.getenv("TOKEN")
    if not token:
        logger.critical("TOKEN not set in .env file. Exiting.")
        return

    bot = FangYuan()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
