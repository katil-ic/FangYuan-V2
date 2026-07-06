"""
Embed Builder - Interactive embed creator and sender
"""

import discord
from discord.ext import commands
import asyncio
import json
from datetime import datetime
from utils.helpers import make_embed, load_json, save_json

SAVED_EMBEDS_FILE = "data/saved_embeds.json"


class EmbedBuilder(discord.ui.View):
    def __init__(self, ctx, embed: discord.Embed):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.embed = embed
        self.target_channel = ctx.channel

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    @discord.ui.button(label="Set Title", style=discord.ButtonStyle.primary, emoji="<:ownerinfo:1523725199457910884>")
    async def set_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Enter the **title** for the embed:", ephemeral=True)
        msg = await self.ctx.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=60)
        self.embed.title = msg.content
        await msg.delete()
        await self._refresh(interaction)

    @discord.ui.button(label="Set Description", style=discord.ButtonStyle.primary, emoji="<:ownerinfo:1523725199457910884>")
    async def set_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Enter the **description** (supports markdown, use \\n for newlines):", ephemeral=True)
        msg = await self.ctx.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=120)
        self.embed.description = msg.content.replace("\\n", "\n")
        await msg.delete()
        await self._refresh(interaction)

    @discord.ui.button(label="Set Color", style=discord.ButtonStyle.primary, emoji="<:ownerinfo:1523725199457910884>")
    async def set_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Enter a **hex color** (e.g. `#5865F2`):", ephemeral=True)
        msg = await self.ctx.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=60)
        try:
            self.embed.color = int(msg.content.replace("#", ""), 16)
        except ValueError:
            pass
        await msg.delete()
        await self._refresh(interaction)

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.secondary, emoji="<a:pink_arrow_haveli:1523620310124068985>")
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Enter field in format: `Name | Value | inline(true/false)`", ephemeral=True)
        msg = await self.ctx.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=60)
        parts = msg.content.split("|")
        if len(parts) >= 2:
            name = parts[0].strip()
            value = parts[1].strip()
            inline = len(parts) > 2 and parts[2].strip().lower() == "true"
            self.embed.add_field(name=name, value=value, inline=inline)
        await msg.delete()
        await self._refresh(interaction)

    @discord.ui.button(label="Clear Fields", style=discord.ButtonStyle.secondary, emoji="<:ownerinfo:1523725199457910884>")
    async def clear_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed.clear_fields()
        await self._refresh(interaction)

    @discord.ui.button(label="Set Image", style=discord.ButtonStyle.secondary, emoji="<:ownerinfo:1523725199457910884>")
    async def set_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Enter the **image URL** (or `none` to remove):", ephemeral=True)
        msg = await self.ctx.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=60)
        if msg.content.lower() == "none":
            self.embed.set_image(url=None)
        else:
            self.embed.set_image(url=msg.content)
        await msg.delete()
        await self._refresh(interaction)

    @discord.ui.button(label="Set Thumbnail", style=discord.ButtonStyle.secondary, emoji="<:ownerinfo:1523725199457910884>")
    async def set_thumbnail(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Enter the **thumbnail URL** (or `none` to remove):", ephemeral=True)
        msg = await self.ctx.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=60)
        if msg.content.lower() == "none":
            self.embed.set_thumbnail(url=None)
        else:
            self.embed.set_thumbnail(url=msg.content)
        await msg.delete()
        await self._refresh(interaction)

    @discord.ui.button(label="Set Footer", style=discord.ButtonStyle.secondary, emoji="<:ownerinfo:1523725199457910884>")
    async def set_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Enter the **footer text** (optionally `text | icon_url`):", ephemeral=True)
        msg = await self.ctx.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=60)
        parts = msg.content.split("|")
        text = parts[0].strip()
        icon = parts[1].strip() if len(parts) > 1 else None
        self.embed.set_footer(text=text, icon_url=icon)
        await msg.delete()
        await self._refresh(interaction)

    @discord.ui.button(label="Set Author", style=discord.ButtonStyle.secondary, emoji="<:strangerz_girl_staff:1523386969101697174>")
    async def set_author(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Enter: `name | icon_url (optional) | url (optional)`", ephemeral=True)
        msg = await self.ctx.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=60)
        parts = [p.strip() for p in msg.content.split("|")]
        name = parts[0]
        icon = parts[1] if len(parts) > 1 else None
        url = parts[2] if len(parts) > 2 else None
        self.embed.set_author(name=name, icon_url=icon or discord.Embed.Empty, url=url or discord.Embed.Empty)
        await msg.delete()
        await self._refresh(interaction)

    @discord.ui.button(label="Toggle Timestamp", style=discord.ButtonStyle.secondary, emoji="<:ownerinfo:1523725199457910884>")
    async def toggle_timestamp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.embed.timestamp:
            self.embed.timestamp = discord.Embed.Empty
        else:
            self.embed.timestamp = datetime.utcnow()
        await self._refresh(interaction)

    @discord.ui.button(label="Set Channel", style=discord.ButtonStyle.success, emoji="<a:Announce:1520896619829002240>")
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Mention the channel to send to (e.g. `#general`):", ephemeral=True)
        msg = await self.ctx.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=30)
        if msg.channel_mentions:
            self.target_channel = msg.channel_mentions[0]
        await msg.delete()
        await interaction.followup.send(f"<a:tick:1523383850749792397> Target channel set to {self.target_channel.mention}", ephemeral=True)

    @discord.ui.button(label="<a:tick:1523383850749792397> Send", style=discord.ButtonStyle.success, emoji="<:ownerinfo:1523725199457910884>")
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.embed.title and not self.embed.description:
            return await interaction.response.send_message("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Add a title or description first.", ephemeral=True)
        await self.target_channel.send(embed=self.embed)
        await interaction.response.send_message(f"<a:tick:1523383850749792397> Embed sent to {self.target_channel.mention}!", ephemeral=True)
        self.stop()

    @discord.ui.button(label="<:ownerinfo:1523725199457910884> Save", style=discord.ButtonStyle.success, emoji="<:ownerinfo:1523725199457910884>")
    async def save_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Enter a **name** to save this embed as:", ephemeral=True)
        msg = await self.ctx.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=30)
        name = msg.content.strip().lower().replace(" ", "_")
        await msg.delete()
        saved = load_json(SAVED_EMBEDS_FILE)
        guild_id = str(self.ctx.guild.id)
        if guild_id not in saved:
            saved[guild_id] = {}
        saved[guild_id][name] = embed_to_dict(self.embed)
        save_json(SAVED_EMBEDS_FILE, saved)
        await interaction.followup.send(f"<a:tick:1523383850749792397> Embed saved as `{name}`!", ephemeral=True)

    @discord.ui.button(label="<:Xieron_stolen_emoji_1774597520:1520895245733204039> Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        self.stop()

    async def _refresh(self, interaction: discord.Interaction):
        try:
            await interaction.message.edit(embed=self.embed)
        except Exception:
            pass


def embed_to_dict(embed: discord.Embed) -> dict:
    return embed.to_dict()


def dict_to_embed(d: dict) -> discord.Embed:
    return discord.Embed.from_dict(d)


class Embeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="embed", aliases=["embedbuilder", "eb"])
    @commands.has_permissions(manage_messages=True)
    async def embed_command(self, ctx):
        """Open the interactive embed builder."""
        embed = discord.Embed(
            title="<:ownerinfo:1523725199457910884> Embed Preview",
            description="Use the buttons below to customize this embed, then send it.",
            color=0x5865F2
        )
        view = EmbedBuilder(ctx, embed)
        msg = await ctx.send(embed=embed, view=view)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.hybrid_command(name="embedsend")
    @commands.has_permissions(manage_messages=True)
    async def embedsend(self, ctx, channel: discord.TextChannel, *, json_text: str):
        """Send a raw JSON embed to a channel. Use `!embedjson` to get the format."""
        try:
            data = json.loads(json_text)
            embed = discord.Embed.from_dict(data)
            await channel.send(embed=embed)
            await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Embed sent to {channel.mention}.", self.bot.success_color))
        except json.JSONDecodeError:
            await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Invalid JSON.", self.bot.error_color))
        except Exception as e:
            await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> Error: {e}", self.bot.error_color))

    @commands.hybrid_command(name="embeds", aliases=["savedembeds"])
    @commands.has_permissions(manage_messages=True)
    async def list_embeds(self, ctx):
        """List all saved embeds for this server."""
        saved = load_json(SAVED_EMBEDS_FILE)
        guild_id = str(ctx.guild.id)
        embeds = saved.get(guild_id, {})
        if not embeds:
            return await ctx.send(embed=make_embed("No saved embeds. Use `!embed` to build and save one.", 0x5865F2))
        embed = discord.Embed(title="<:ownerinfo:1523725199457910884> Saved Embeds", color=0x5865F2)
        embed.description = "\n".join(f"• `{name}` — !embedload {name}" for name in embeds.keys())
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="embedload")
    @commands.has_permissions(manage_messages=True)
    async def embedload(self, ctx, name: str, channel: discord.TextChannel = None):
        """Load and send a saved embed."""
        saved = load_json(SAVED_EMBEDS_FILE)
        guild_id = str(ctx.guild.id)
        e_data = saved.get(guild_id, {}).get(name.lower())
        if not e_data:
            return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> No saved embed named `{name}`.", self.bot.error_color))
        embed = dict_to_embed(e_data)
        target = channel or ctx.channel
        await target.send(embed=embed)
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Embed `{name}` sent to {target.mention}.", self.bot.success_color))

    @commands.hybrid_command(name="embeddelete")
    @commands.has_permissions(manage_messages=True)
    async def embeddelete(self, ctx, name: str):
        """Delete a saved embed."""
        saved = load_json(SAVED_EMBEDS_FILE)
        guild_id = str(ctx.guild.id)
        if name.lower() in saved.get(guild_id, {}):
            del saved[guild_id][name.lower()]
            save_json(SAVED_EMBEDS_FILE, saved)
            await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Deleted embed `{name}`.", self.bot.success_color))
        else:
            await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> No embed named `{name}`.", self.bot.error_color))

    @commands.hybrid_command(name="say")
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, channel: discord.TextChannel, *, message: str):
        """Send a plain text message to a channel."""
        await channel.send(message)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.hybrid_command(name="sayhere")
    @commands.has_permissions(manage_messages=True)
    async def sayhere(self, ctx, *, message: str):
        """Send a plain text message in the current channel."""
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await ctx.send(message)

    @commands.hybrid_command(name="embedjson")
    @commands.has_permissions(manage_messages=True)
    async def embedjson(self, ctx):
        """Show an example JSON format for embed sending."""
        example = {
            "title": "My Title",
            "description": "My description here.\nSupports **markdown**.",
            "color": 5793266,
            "fields": [
                {"name": "Field 1", "value": "Value 1", "inline": True},
                {"name": "Field 2", "value": "Value 2", "inline": True}
            ],
            "footer": {"text": "Footer text"},
            "thumbnail": {"url": "https://example.com/image.png"}
        }
        await ctx.send(f"```json\n{json.dumps(example, indent=2)}\n```\nUse with: `!embedsend #channel <json>`")

    @commands.hybrid_command(name="editmessage")
    @commands.has_permissions(manage_messages=True)
    async def editmessage(self, ctx, message_id: int, *, new_content: str):
        """Edit a message the bot sent."""
        try:
            msg = await ctx.channel.fetch_message(message_id)
            if msg.author != ctx.guild.me:
                return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> I can only edit my own messages.", self.bot.error_color))
            await msg.edit(content=new_content)
            try:
                await ctx.message.delete()
            except Exception:
                pass
        except discord.NotFound:
            await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Message not found.", self.bot.error_color))


async def setup(bot):
    await bot.add_cog(Embeds(bot))
