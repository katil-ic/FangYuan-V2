"""
Shared helper utilities for FangYuan V2
"""

import discord
from discord.ext import commands
import json
import os
from datetime import timedelta


def make_embed(description: str, color: int = 0x5865F2) -> discord.Embed:
    """Create a simple single-description embed."""
    return discord.Embed(description=description, color=color)


def load_json(path: str) -> dict:
    """Load a JSON file, returning an empty dict if not found."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_json(path: str, data: dict) -> None:
    """Save data to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def format_duration(seconds: int) -> str:
    """Format seconds into a human-readable duration string."""
    delta = timedelta(seconds=seconds)
    d = delta.days
    h, remainder = divmod(delta.seconds, 3600)
    m, s = divmod(remainder, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s:
        parts.append(f"{s}s")
    return " ".join(parts) or "0s"


def truncate(text: str, max_len: int = 1024) -> str:
    """Truncate a string to fit within Discord embed limits."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def paginate(items: list, per_page: int = 10) -> list:
    """Split a list into pages."""
    return [items[i:i + per_page] for i in range(0, len(items), per_page)]


def escape_markdown(text: str) -> str:
    """Escape Discord markdown characters."""
    chars = r"\*_`~|>"
    return "".join(f"\\{c}" if c in chars else c for c in text)


def has_any_role(*role_ids):
    """Check decorator — user has any of the given role IDs."""
    async def predicate(ctx):
        if ctx.guild is None:
            return False
        return any(role.id in role_ids for role in ctx.author.roles)
    return commands.check(predicate)
