"""
Autoresponder System - Keyword-triggered auto-responses
"""

import discord
from discord.ext import commands
import re
from utils.helpers import make_embed, load_json, save_json

AR_FILE = "data/autoresponder.json"


class Autoresponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cache = {}

    def get_guild_rules(self, guild_id: str):
        if guild_id not in self._cache:
            data = load_json(AR_FILE)
            self._cache[guild_id] = data.get(guild_id, [])
        return self._cache[guild_id]

    def _invalidate(self, guild_id: str):
        self._cache.pop(guild_id, None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        rules = self.get_guild_rules(guild_id)

        for rule in rules:
            if not rule.get("enabled", True):
                continue

            trigger = rule["trigger"]
            content = message.content

            match_type = rule.get("match_type", "contains")
            if match_type == "exact":
                matched = content.lower() == trigger.lower()
            elif match_type == "startswith":
                matched = content.lower().startswith(trigger.lower())
            elif match_type == "endswith":
                matched = content.lower().endswith(trigger.lower())
            elif match_type == "regex":
                try:
                    matched = bool(re.search(trigger, content, re.IGNORECASE))
                except re.error:
                    matched = False
            else:  # contains
                matched = trigger.lower() in content.lower()

            if not matched:
                continue

            # Channel restriction
            allowed_channels = rule.get("channels", [])
            if allowed_channels and str(message.channel.id) not in allowed_channels:
                continue

            response = rule["response"]
            response = response.replace("{user}", message.author.mention)
            response = response.replace("{username}", str(message.author))
            response = response.replace("{server}", message.guild.name)

            # Delete trigger message?
            if rule.get("delete_trigger"):
                try:
                    await message.delete()
                except Exception:
                    pass

            # Respond as embed or plain
            if rule.get("embed"):
                embed = discord.Embed(
                    description=response,
                    color=int(rule.get("embed_color", "0x5865F2"), 16)
                    if isinstance(rule.get("embed_color"), str)
                    else rule.get("embed_color", 0x5865F2)
                )
                if rule.get("embed_title"):
                    embed.title = rule["embed_title"]
                target = message.channel
                if rule.get("reply"):
                    await message.reply(embed=embed, mention_author=False)
                else:
                    await target.send(embed=embed)
            else:
                if rule.get("reply"):
                    await message.reply(response, mention_author=False)
                else:
                    await message.channel.send(response)

            # Only match first rule?
            if rule.get("stop_after_match", True):
                break

    # ─── COMMANDS ─────────────────────────────────────────────────────────────

    @commands.hybrid_group(name="ar", aliases=["autoresponder", "autoresponse"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def ar_group(self, ctx):
        await self._show_list(ctx)

    @ar_group.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def ar_add(self, ctx, trigger: str, *, response: str):
        """Add an autoresponder rule. Match type defaults to 'contains'."""
        data = load_json(AR_FILE)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            data[guild_id] = []

        if any(r["trigger"].lower() == trigger.lower() for r in data[guild_id]):
            return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> A rule for `{trigger}` already exists. Remove it first.", self.bot.error_color))

        data[guild_id].append({
            "trigger": trigger,
            "response": response,
            "match_type": "contains",
            "enabled": True,
            "reply": False,
            "delete_trigger": False,
            "embed": False,
        })
        save_json(AR_FILE, data)
        self._invalidate(guild_id)
        embed = discord.Embed(title="<a:tick:1523383850749792397> Autoresponder Added", color=self.bot.success_color)
        embed.add_field(name="Trigger", value=f"`{trigger}`", inline=True)
        embed.add_field(name="Response", value=response[:100], inline=False)
        await ctx.send(embed=embed)

    @ar_group.command(name="addexact")
    @commands.has_permissions(manage_guild=True)
    async def ar_addexact(self, ctx, trigger: str, *, response: str):
        """Add an exact-match autoresponder."""
        await self._ar_add_typed(ctx, trigger, response, "exact")

    @ar_group.command(name="addregex")
    @commands.has_permissions(manage_guild=True)
    async def ar_addregex(self, ctx, trigger: str, *, response: str):
        """Add a regex-match autoresponder."""
        try:
            re.compile(trigger)
        except re.error:
            return await ctx.send(embed=make_embed("<:Xieron_stolen_emoji_1774597520:1520895245733204039> Invalid regex pattern.", self.bot.error_color))
        await self._ar_add_typed(ctx, trigger, response, "regex")

    async def _ar_add_typed(self, ctx, trigger, response, match_type):
        data = load_json(AR_FILE)
        guild_id = str(ctx.guild.id)
        if guild_id not in data:
            data[guild_id] = []
        data[guild_id].append({
            "trigger": trigger,
            "response": response,
            "match_type": match_type,
            "enabled": True,
            "reply": False,
            "delete_trigger": False,
            "embed": False,
        })
        save_json(AR_FILE, data)
        self._invalidate(guild_id)
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Added `{match_type}` rule for `{trigger}`.", self.bot.success_color))

    @ar_group.command(name="remove", aliases=["delete"])
    @commands.has_permissions(manage_guild=True)
    async def ar_remove(self, ctx, *, trigger: str):
        data = load_json(AR_FILE)
        guild_id = str(ctx.guild.id)
        before = len(data.get(guild_id, []))
        data[guild_id] = [r for r in data.get(guild_id, []) if r["trigger"].lower() != trigger.lower()]
        if len(data.get(guild_id, [])) == before:
            return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> No rule found for `{trigger}`.", self.bot.error_color))
        save_json(AR_FILE, data)
        self._invalidate(guild_id)
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Removed autoresponder for `{trigger}`.", self.bot.success_color))

    @ar_group.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def ar_list(self, ctx):
        await self._show_list(ctx)

    async def _show_list(self, ctx):
        data = load_json(AR_FILE)
        guild_id = str(ctx.guild.id)
        rules = data.get(guild_id, [])
        if not rules:
            return await ctx.send(embed=make_embed("No autoresponders configured. Use `!ar add <trigger> <response>`.", 0x5865F2))

        embed = discord.Embed(title=f"🤖 Autoresponders ({len(rules)})", color=0x5865F2)
        lines = []
        for i, r in enumerate(rules, 1):
            status = "<a:tick:1523383850749792397>" if r.get("enabled", True) else "<:Xieron_stolen_emoji_1774597520:1520895245733204039>"
            match_icon = {"exact": "🎯", "startswith": "⬅️", "endswith": "<a:pink_arrow_haveli:1523620310124068985>", "regex": "🔣", "contains": "🔍"}.get(r.get("match_type", "contains"), "🔍")
            lines.append(f"{status} `#{i}` {match_icon} **{r['trigger']}** → {r['response'][:50]}")
        embed.description = "\n".join(lines)
        embed.set_footer(text="!ar add/remove/enable/disable/info")
        await ctx.send(embed=embed)

    @ar_group.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    async def ar_enable(self, ctx, *, trigger: str):
        await self._set_enabled(ctx, trigger, True)

    @ar_group.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    async def ar_disable(self, ctx, *, trigger: str):
        await self._set_enabled(ctx, trigger, False)

    async def _set_enabled(self, ctx, trigger, state):
        data = load_json(AR_FILE)
        guild_id = str(ctx.guild.id)
        found = False
        for r in data.get(guild_id, []):
            if r["trigger"].lower() == trigger.lower():
                r["enabled"] = state
                found = True
                break
        if not found:
            return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> No rule for `{trigger}`.", self.bot.error_color))
        save_json(AR_FILE, data)
        self._invalidate(guild_id)
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Rule `{trigger}` {'enabled' if state else 'disabled'}.", self.bot.success_color))

    @ar_group.command(name="toggle_reply")
    @commands.has_permissions(manage_guild=True)
    async def ar_togglereply(self, ctx, *, trigger: str):
        """Toggle whether the bot replies (mentions) or just sends."""
        data = load_json(AR_FILE)
        guild_id = str(ctx.guild.id)
        for r in data.get(guild_id, []):
            if r["trigger"].lower() == trigger.lower():
                r["reply"] = not r.get("reply", False)
                save_json(AR_FILE, data)
                self._invalidate(guild_id)
                return await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Reply mode {'on' if r['reply'] else 'off'} for `{trigger}`.", self.bot.success_color))
        await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> No rule for `{trigger}`.", self.bot.error_color))

    @ar_group.command(name="toggle_embed")
    @commands.has_permissions(manage_guild=True)
    async def ar_toggleembed(self, ctx, *, trigger: str):
        """Toggle embed mode for a rule."""
        data = load_json(AR_FILE)
        guild_id = str(ctx.guild.id)
        for r in data.get(guild_id, []):
            if r["trigger"].lower() == trigger.lower():
                r["embed"] = not r.get("embed", False)
                save_json(AR_FILE, data)
                self._invalidate(guild_id)
                return await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Embed mode {'on' if r['embed'] else 'off'} for `{trigger}`.", self.bot.success_color))
        await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> No rule for `{trigger}`.", self.bot.error_color))

    @ar_group.command(name="toggle_delete")
    @commands.has_permissions(manage_guild=True)
    async def ar_toggledelete(self, ctx, *, trigger: str):
        """Toggle whether the trigger message is deleted."""
        data = load_json(AR_FILE)
        guild_id = str(ctx.guild.id)
        for r in data.get(guild_id, []):
            if r["trigger"].lower() == trigger.lower():
                r["delete_trigger"] = not r.get("delete_trigger", False)
                save_json(AR_FILE, data)
                self._invalidate(guild_id)
                return await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Delete trigger {'on' if r['delete_trigger'] else 'off'} for `{trigger}`.", self.bot.success_color))
        await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> No rule for `{trigger}`.", self.bot.error_color))

    @ar_group.command(name="info")
    @commands.has_permissions(manage_guild=True)
    async def ar_info(self, ctx, *, trigger: str):
        """Show detailed info about an autoresponder rule."""
        data = load_json(AR_FILE)
        guild_id = str(ctx.guild.id)
        rule = next((r for r in data.get(guild_id, []) if r["trigger"].lower() == trigger.lower()), None)
        if not rule:
            return await ctx.send(embed=make_embed(f"<:Xieron_stolen_emoji_1774597520:1520895245733204039> No rule for `{trigger}`.", self.bot.error_color))
        embed = discord.Embed(title=f"📋 Autoresponder: {rule['trigger']}", color=0x5865F2)
        embed.add_field(name="Trigger", value=f"`{rule['trigger']}`", inline=True)
        embed.add_field(name="Match Type", value=rule.get("match_type", "contains"), inline=True)
        embed.add_field(name="Enabled", value="<a:tick:1523383850749792397>" if rule.get("enabled", True) else "<:Xieron_stolen_emoji_1774597520:1520895245733204039>", inline=True)
        embed.add_field(name="Reply Mode", value="<a:tick:1523383850749792397>" if rule.get("reply") else "<:Xieron_stolen_emoji_1774597520:1520895245733204039>", inline=True)
        embed.add_field(name="Embed Mode", value="<a:tick:1523383850749792397>" if rule.get("embed") else "<:Xieron_stolen_emoji_1774597520:1520895245733204039>", inline=True)
        embed.add_field(name="Delete Trigger", value="<a:tick:1523383850749792397>" if rule.get("delete_trigger") else "<:Xieron_stolen_emoji_1774597520:1520895245733204039>", inline=True)
        embed.add_field(name="Response", value=rule["response"][:500], inline=False)
        await ctx.send(embed=embed)

    @ar_group.command(name="clear")
    @commands.has_permissions(administrator=True)
    async def ar_clear(self, ctx):
        """Clear ALL autoresponders for this server."""
        data = load_json(AR_FILE)
        guild_id = str(ctx.guild.id)
        count = len(data.get(guild_id, []))
        data[guild_id] = []
        save_json(AR_FILE, data)
        self._invalidate(guild_id)
        await ctx.send(embed=make_embed(f"<a:tick:1523383850749792397> Cleared {count} autoresponder(s).", self.bot.success_color))


async def setup(bot):
    await bot.add_cog(Autoresponder(bot))
