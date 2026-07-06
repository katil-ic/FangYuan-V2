# 🤖 FangYuan V2 — All-in-One Discord Bot

A powerful, professional Discord bot built to handle entire public servers single-handedly.

---

## ✨ Feature Overview

| System | Commands |
|---|---|
| 🛡️ **Moderation** | ban, tempban, unban, kick, mute, unmute, warn, warnings, clearwarns, purge, lock, unlock, lockall, slowmode, nick, addrole, removerole, nuke, setmodlog |
| 🎫 **Ticket System** | ticketpanel, ticketsetup, addtoticket, removefromticket, ticketstats |
| 🎉 **Welcome System** | welcome setchannel/setmessage/settitle/enable/disable/ping/test/setcolor, leave, autorole, dmwelcome |
| 📝 **Embed Builder** | embed (interactive), embedsend, embeds, embedload, embeddelete, say, sayhere, embedjson, editmessage |
| 🤖 **Autoresponder** | ar add/addexact/addregex/remove/list/enable/disable/toggle_reply/toggle_embed/toggle_delete/info/clear |
| 📢 **Announcements** | announce, announceembed, annrole, broadcast, setannchannel, quickann, updatelog |
| 💰 **Crypto Utility** | ball (special), cryptoinfo, convert, cryptotop, gasfee |
| 🎊 **Giveaways** | gstart, gend, greroll, glist, gdelete, ginfo |
| 📊 **Polls** | poll, quickpoll, endpoll, strawpoll |
| 🎭 **Roles** | reactionrole, rrremove, rrlist, rrpanel, massrole, massunrole, temprole, rolecolor, rolename, createrole, delrole |
| ℹ️ **Info** | serverinfo, userinfo, avatar, banner, roleinfo, channelinfo, botinfo, permissions, emojis |
| 🔧 **Utility** | help, ping, uptime, remind, snipe, editsnipe, afk, afklist, inviteinfo, membercount, charinfo, timestamp |

---

## 🔮 Special Feature: `.ball [address]`

The `.ball` command checks a crypto address for:
- **Last 1-hour received** — how much was received in the past hour
- **Last 1-hour sent** — how much was sent in the past hour
- **Pending/unconfirmed** — pending balance
- **All-time totals** — total received + total spent since creation
- **Current balance** — live balance in both crypto and USD

**Supported chains:** `eth` `btc` `bsc` `matic`

```
.ball 0x742d35Cc6634C0532925a3b844Bc454e4438f44e eth
.ball 1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf Na btc
.ball 0x... bsc
.ball 0x... matic
```

Chain is auto-detected from the address format if not specified.

---

## 🚀 Hosting on Railway (Recommended — Free)

Railway is the easiest way to host your bot 24/7 for free.

### Step 1 — Create a GitHub repo

1. Go to [github.com](https://github.com) → **New repository**
2. Name it `fangyuan-v2` (private is fine)
3. Do **not** add a README (keep it empty)

### Step 2 — Upload the bot files

You have two options:

**Option A — GitHub web upload (easiest, no Git needed):**
1. Open your new repo on GitHub
2. Click **Add file → Upload files**
3. Drag and drop **all files from inside this ZIP** (not the ZIP itself)
4. Click **Commit changes**

**Option B — Git CLI:**
```bash
unzip FangYuanV2.zip
cd bot
git init
git remote add origin https://github.com/YOURUSERNAME/fangyuan-v2.git
git add .
git commit -m "initial commit"
git push -u origin main
```

### Step 3 — Deploy on Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **New Project → Deploy from GitHub repo**
3. Select your `fangyuan-v2` repo
4. Railway will detect Python automatically — click **Deploy**

### Step 4 — Set environment variables

In your Railway project:
1. Click on your service → **Variables** tab
2. Add these variables one by one:

| Variable | Value |
|---|---|
| `TOKEN` | Your Discord bot token |
| `PREFIX` | `!` (or your choice) |
| `OWNER_IDS` | Your Discord user ID |
| `ETHERSCAN_API_KEY` | From etherscan.io/apis (optional) |
| `BSCSCAN_API_KEY` | From bscscan.com/apis (optional) |
| `POLYGONSCAN_API_KEY` | From polygonscan.com/apis (optional) |

3. Railway will automatically redeploy after you add variables

### Step 5 — Done! ✅

Click **Deployments** tab and watch the logs. You should see:
```
Logged in as FangYuan V2#XXXX
Synced slash commands
Bot is ready!
```

> **Railway free tier** gives you $5/month of free credits — enough to run a Discord bot 24/7 all month.

---

## 💻 Local / Pterodactyl Setup

### Prerequisites
- Python 3.10+
- A Discord bot token from [Discord Developer Portal](https://discord.com/developers/applications)
- (Optional) Etherscan/BscScan/PolygonScan API keys for EVM chain support

### Local Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
nano .env   # Fill in your TOKEN and other values

# 3. Start the bot
python main.py
```

### Pterodactyl Panel Setup

1. Create a new server using the **Python** egg
2. Set startup command: `python main.py`
3. Upload all files from this ZIP to your server
4. Add your environment variables in the **Startup** tab:
   - `TOKEN` = your bot token
   - `PREFIX` = `!` (or whatever you prefer)
   - `OWNER_IDS` = your Discord user ID
5. Start the server

---

## ⚙️ Configuration

All config is stored in the `data/` folder as JSON files automatically created on first use:

| File | Purpose |
|---|---|
| `data/config.json` | General server config (mod log, etc.) |
| `data/tickets.json` | Ticket system config + open tickets |
| `data/welcome.json` | Welcome/leave/DM/autorole config |
| `data/autoresponder.json` | Autoresponder rules |
| `data/reaction_roles.json` | Reaction role mappings |
| `data/announcements.json` | Announcement channel config |
| `data/giveaways.json` | Active and past giveaways |
| `data/polls.json` | Active and past polls |
| `data/warns.json` | Member warnings |
| `data/saved_embeds.json` | Saved embed templates |

---

## 🛡️ Permissions Required

The bot needs these permissions:
- **Administrator** (easiest) OR manually:
  - Manage Roles
  - Manage Channels
  - Manage Messages
  - Manage Nicknames
  - Ban Members
  - Kick Members
  - Moderate Members (for timeout/mute)
  - Read Message History
  - Send Messages
  - Embed Links
  - Attach Files
  - Add Reactions
  - Use External Emojis

---

## 📋 Quick Setup Guide

After inviting the bot to your server:

```
# 1. Set up mod logging
!setmodlog #mod-logs

# 2. Set up welcome messages
!welcome setchannel #welcome
!welcome setmessage Welcome {user} to {server}! You are member #{count}.
!welcome settitle Welcome to Our Server!
!welcome enable

# 3. Set up leave messages
!leave setchannel #goodbye
!leave setmessage {username} has left the server. Goodbye!
!leave enable

# 4. Set up auto-roles on join
!autorole add @Member

# 5. Set up ticket system
!ticketsetup #ticket-category @Support #ticket-logs
!ticketpanel   (sends the panel in the current channel)

# 6. Add autoresponders
!ar add hello Hey there {user}! 👋

# 7. Set up announcement channel
!setannchannel #announcements

# 8. Start a giveaway
!gstart 24h 1w #giveaways Free Discord Nitro

# 9. Create a reaction role panel
!rrpanel #roles Pick Your Roles
```

---

## 🔑 API Keys

| Feature | API Key Needed | Where to Get |
|---|---|---|
| ETH address lookup | `ETHERSCAN_API_KEY` | [etherscan.io/apis](https://etherscan.io/apis) |
| BSC address lookup | `BSCSCAN_API_KEY` | [bscscan.com/apis](https://bscscan.com/apis) |
| Polygon address lookup | `POLYGONSCAN_API_KEY` | [polygonscan.com/apis](https://polygonscan.com/apis) |
| BTC address lookup | ❌ Not needed | Uses Blockchain.info |
| Crypto prices | ❌ Not needed | Uses CoinGecko free tier |

All API keys are **free** to get.

---

## 📄 License

Built for personal and server use. FangYuan V2 — by request.
