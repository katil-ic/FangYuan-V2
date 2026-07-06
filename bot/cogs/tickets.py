"""
Ticket System - Professional ticket management
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io
import json
import os
from datetime import datetime
from utils.helpers import make_embed, load_json, save_json

TICKET_CONFIG_FILE = "data/tickets.json"


class TicketCloseView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="<:ownerinfo:1480905030713212938> Close Ticket", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = load_json(TICKET_CONFIG_FILE)
        guild_id = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        ticket_data = cfg.get(guild_id, {}).get("open_tickets", {}).get(channel_id)

        if not ticket_data:
            return await interaction.response.send_message("<:Xieron_stolen_emoji_1774597520:1520895245733204039> This doesn't look like an active ticket.", ephemeral=True)

        is_staff = interaction.user.guild_permissions.manage_channels
        is_owner = str(interaction.user.id) == ticket_data.get("user_id")
        if not is_staff and not is_owner:
            return await interaction.response.send_message("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Only staff or the ticket owner can close this.", ephemeral=True)

        await interaction.response.send_message(embed=make_embed("<:ownerinfo:1480905030713212938> Closing ticket in 5 seconds...", 0xED4245))
        await asyncio.sleep(5)

        # Save transcript
        transcript_lines = []
        async for msg in interaction.channel.history(limit=500, oldest_first=True):
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            transcript_lines.append(f"[{ts}] {msg.author} ({msg.author.id}): {msg.content}")
            for embed in msg.embeds:
                if embed.description:
                    transcript_lines.append(f"  [EMBED] {embed.description}")
        transcript = "\n".join(transcript_lines)

        # Send transcript to log channel
        log_channel_id = cfg.get(guild_id, {}).get("log_channel")
        if log_channel_id:
            log_channel = interaction.guild.get_channel(int(log_channel_id))
            if log_channel:
                file = discord.File(io.StringIO(transcript), filename=f"transcript-{interaction.channel.name}.txt")
                embed = discord.Embed(
                    title="<:ownerinfo:1480905030713212938> Ticket Transcript",
                    description=f"**Channel:** {interaction.channel.name}\n**Closed by:** {interaction.user.mention}\n**Owner:** <@{ticket_data.get('user_id')}>",
                    color=0x5865F2,
                    timestamp=datetime.utcnow()
                )
                await log_channel.send(embed=embed, file=file)

        # DM transcript to user
        try:
            user = await interaction.guild.fetch_member(int(ticket_data.get("user_id")))
            file2 = discord.File(io.StringIO(transcript), filename=f"transcript-{interaction.channel.name}.txt")
            await user.send(
                embed=make_embed(f"<:ownerinfo:1480905030713212938> Your ticket in **{interaction.guild.name}** has been closed. Transcript attached.", 0x5865F2),
                file=file2
            )
        except Exception:
            pass

        # Remove from open tickets
        cfg[guild_id]["open_tickets"].pop(channel_id, None)
        save_json(TICKET_CONFIG_FILE, cfg)

        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

    @discord.ui.button(label="<:ownerinfo:1480905030713212938> Transcript", style=discord.ButtonStyle.secondary, custom_id="ticket:transcript")
    async def get_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Staff only.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        lines = []
        async for msg in interaction.channel.history(limit=500, oldest_first=True):
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{ts}] {msg.author}: {msg.content}")
        transcript = "\n".join(lines)
        file = discord.File(io.StringIO(transcript), filename=f"transcript-{interaction.channel.name}.txt")
        await interaction.followup.send(file=file, ephemeral=True)

    @discord.ui.button(label="Add User", emoji="<a:pink_arrow_haveli:1523620310124068985>", style=discord.ButtonStyle.primary, custom_id="ticket:adduser")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Staff only.", ephemeral=True)
        await interaction.response.send_message("Mention the user(s) to add (e.g. `@User`):", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=30)
            for mention in msg.mentions:
                await interaction.channel.set_permissions(mention, read_messages=True, send_messages=True)
            await interaction.channel.send(embed=make_embed(f"<a:tick:1523383850749792397> Added {', '.join(m.mention for m in msg.mentions)} to the ticket.", 0x57F287))
        except asyncio.TimeoutError:
            pass


class TicketOpenView(discord.ui.View):
    def __init__(self, bot, category_id=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.category_id = category_id

    @discord.ui.button(label="<a:tickets1:1418334460285419541> Open Ticket", style=discord.ButtonStyle.primary, custom_id="ticket:open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        cfg = load_json(TICKET_CONFIG_FILE)
        guild_id = str(guild.id)

        if guild_id not in cfg:
            cfg[guild_id] = {}
        if "open_tickets" not in cfg[guild_id]:
            cfg[guild_id]["open_tickets"] = {}

        # Check if user already has an open ticket
        for ch_id, td in cfg[guild_id]["open_tickets"].items():
            if td.get("user_id") == str(interaction.user.id):
                ch = guild.get_channel(int(ch_id))
                if ch:
                    return await interaction.response.send_message(
                        f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> You already have an open ticket: {ch.mention}", ephemeral=True
                    )

        # Determine category
        category = None
        cat_id = cfg.get(guild_id, {}).get("ticket_category")
        if cat_id:
            category = guild.get_channel(int(cat_id))

        # Get support role
        support_role_id = cfg.get(guild_id, {}).get("support_role")
        support_role = guild.get_role(int(support_role_id)) if support_role_id else None

        # Create ticket channel
        ticket_num = cfg[guild_id].get("ticket_count", 0) + 1
        cfg[guild_id]["ticket_count"] = ticket_num

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{ticket_num:04d}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket by {interaction.user} ({interaction.user.id})"
        )

        # Save ticket data
        cfg[guild_id]["open_tickets"][str(channel.id)] = {
            "user_id": str(interaction.user.id),
            "ticket_num": ticket_num,
            "created_at": datetime.utcnow().isoformat()
        }
        save_json(TICKET_CONFIG_FILE, cfg)

        # Send opening message
        embed = discord.Embed(
            title=f"<a:tickets1:1418334460285419541> Ticket #{ticket_num:04d}",
            description=(
                f"Welcome {interaction.user.mention}!\n\n"
                f"Support staff will be with you shortly. Please describe your issue in detail.\n\n"
                f"> **Created by:** {interaction.user.mention}\n"
                f"> **Created at:** <t:{int(datetime.utcnow().timestamp())}:F>"
            ),
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="FangYuan V2 Ticket System")
        if support_role:
            await channel.send(content=support_role.mention, embed=embed, view=TicketCloseView(self.bot))
        else:
            await channel.send(embed=embed, view=TicketCloseView(self.bot))

        await interaction.response.send_message(f"<a:tick:1523383850749792397> Ticket created: {channel.mention}", ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketCloseView(bot))

    @commands.hybrid_command(name="ticketpanel", aliases=["tpanel"])
    @commands.has_permissions(administrator=True)
    async def ticketpanel(self, ctx, *, title: str = "Support Tickets"):
        """Send the ticket panel."""
        embed = discord.Embed(
            title=f"<a:tickets1:1418334460285419541> {title}",
            description=(
                "Need help? Click the button below to open a support ticket.\n\n"
                "**Before opening a ticket:**\n"
                "• Check the FAQ first\n"
                "• Be ready to describe your issue clearly\n"
                "• Our team will respond as soon as possible"
            ),
            color=0x5865F2,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"{ctx.guild.name} • FangYuan V2")
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.send(embed=embed, view=TicketOpenView(self.bot))
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.hybrid_command(name="ticketsetup")
    @commands.has_permissions(administrator=True)
    async def ticketsetup(self, ctx, category: discord.CategoryChannel = None, support_role: discord.Role = None, log_channel: discord.TextChannel = None):
        """Configure the ticket system."""
        cfg = load_json(TICKET_CONFIG_FILE)
        guild_id = str(ctx.guild.id)
        if guild_id not in cfg:
            cfg[guild_id] = {}

        if category:
            cfg[guild_id]["ticket_category"] = str(category.id)
        if support_role:
            cfg[guild_id]["support_role"] = str(support_role.id)
        if log_channel:
            cfg[guild_id]["log_channel"] = str(log_channel.id)

        save_json(TICKET_CONFIG_FILE, cfg)

        embed = discord.Embed(title="<a:tick:1523383850749792397> Ticket System Configured", color=self.bot.success_color)
        embed.add_field(name="Category", value=category.mention if category else "Not set", inline=True)
        embed.add_field(name="Support Role", value=support_role.mention if support_role else "Not set", inline=True)
        embed.add_field(name="Log Channel", value=log_channel.mention if log_channel else "Not set", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="addtoticket")
    @commands.has_permissions(manage_channels=True)
    async def addtoticket(self, ctx, member: discord.Member):
        """Add a user to the current ticket."""
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True, attach_files=True)
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Added {member.mention} to the ticket.", self.bot.success_color))

    @commands.hybrid_command(name="removefromticket")
    @commands.has_permissions(manage_channels=True)
    async def removefromticket(self, ctx, member: discord.Member):
        """Remove a user from the current ticket."""
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Removed {member.mention} from the ticket.", self.bot.success_color))

    @commands.hybrid_command(name="ticketstats")
    @commands.has_permissions(manage_channels=True)
    async def ticketstats(self, ctx):
        """Show ticket statistics."""
        cfg = load_json(TICKET_CONFIG_FILE)
        guild_id = str(ctx.guild.id)
        g_cfg = cfg.get(guild_id, {})
        total = g_cfg.get("ticket_count", 0)
        open_count = len(g_cfg.get("open_tickets", {}))
        embed = discord.Embed(title="<a:tickets1:1418334460285419541> Ticket Statistics", color=0x5865F2)
        embed.add_field(name="Total Tickets", value=str(total), inline=True)
        embed.add_field(name="Open Tickets", value=str(open_count), inline=True)
        embed.add_field(name="Closed Tickets", value=str(total - open_count), inline=True)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
