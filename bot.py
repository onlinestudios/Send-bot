
import os, json, random, re, asyncio
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI

BASE = Path(__file__).parent
DATA = BASE / "data"
APPS_FILE = DATA / "apps.json"
DATA.mkdir(exist_ok=True)

def load_apps():
    if not APPS_FILE.exists():
        APPS_FILE.write_text("{}", encoding="utf-8")
    try:
        return json.loads(APPS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_apps(apps):
    APPS_FILE.write_text(json.dumps(apps, indent=2, ensure_ascii=False), encoding="utf-8")

def invite_url():
    client_id = os.getenv("DISCORD_CLIENT_ID") or "1544335328599343236"
    if not client_id:
        return ""
    permissions = 19456  # Send Messages + Embed Links + Create Public Threads
    return (
        f"https://discord.com/oauth2/authorize?client_id={client_id}"
        f"&permissions={permissions}&scope=bot%20applications.commands"
    )

class SendBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.apps = load_apps()
        self.active = {}  # (guild_id, user_id) -> app code
        self.ai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

    async def setup_hook(self):
        await self.tree.sync()

bot = SendBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")

# /dm
@bot.tree.command(name="dm", description="DM a user in this server")
@app_commands.describe(user="The user to DM", message="The message to send")
async def dm(interaction: discord.Interaction, user: discord.User, message: str):
    try:
        await user.send(message)
        await interaction.response.send_message("✅ DM sent.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I can't DM that user.", ephemeral=True)

# /send
@bot.tree.command(name="send", description="Send a message to a text channel")
@app_commands.describe(channel="The text channel", message="The message to send")
async def send(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need Manage Messages to use this.", ephemeral=True)
        return
    await channel.send(message)
    await interaction.response.send_message("✅ Message sent.", ephemeral=True)

# /forum
@bot.tree.command(name="forum", description="Create a forum post")
@app_commands.describe(channel="The forum channel", title="Post title", message="Post message")
async def forum(interaction: discord.Interaction, channel: discord.ForumChannel, title: str, message: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need Manage Messages to use this.", ephemeral=True)
        return
    await channel.create_thread(name=title[:100], content=message)
    await interaction.response.send_message("✅ Forum post created.", ephemeral=True)

# /invite
@bot.tree.command(name="invite", description="Get the link to invite Send bot")
async def invite(interaction: discord.Interaction):
    url = invite_url()
    if not url:
        await interaction.response.send_message("Invite link is not configured yet.", ephemeral=True)
        return
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Invite Send bot", url=url))
    await interaction.response.send_message("Here is the invite link:", view=view, ephemeral=True)

# /start talk code
start_group = app_commands.Group(name="start", description="Start features")
bot.tree.add_command(start_group)

@start_group.command(name="talk", description="Activate one of your virtual talking apps")
@app_commands.describe(code="Your app code, for example Ahmand#2847")
async def start_talk(interaction: discord.Interaction, code: str):
    code = code.strip()
    app = bot.apps.get(code)
    if not app:
        await interaction.response.send_message(
            "❌ That app code doesn't exist. Create an app on the Send bot website first.",
            ephemeral=True,
        )
        return
    if app.get("owner_discord_id") and str(interaction.user.id) != str(app["owner_discord_id"]):
        await interaction.response.send_message("❌ You don't own that app.", ephemeral=True)
        return

    bot.active[(interaction.guild_id, interaction.user.id)] = code
    await interaction.response.send_message(
        f"✅ **{app['name']}** is ready. Type `@{app['name']} your message` in this server and I'll reply as {code}.\n"
        "Note: this is a virtual app inside Send bot, not a separate Discord bot account.",
        ephemeral=True,
    )

async def ai_reply(app, user_message, author_name):
    if not bot.ai:
        return f"Hi {author_name}! I'm {app['name']}. Add OPENAI_API_KEY to the host to enable AI replies."

    personality = app.get("description") or "Friendly, natural and helpful."
    prompt = (
        f"You are a Discord character called {app['name']}. "
        f"Your personality/description is: {personality}\n"
        "Reply naturally and conversationally. Keep replies reasonably short for Discord. "
        "Do not claim to be a real human or a separate Discord account.\n"
        f"{author_name}: {user_message}"
    )
    response = await bot.ai.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
        instructions=prompt,
        input=user_message,
        store=False,
        max_output_tokens=250,
    )
    return response.output_text.strip() or "I don't know what to say 😭"

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    # Allow either an actual mention of Send bot or typed @AppName.
    content = message.content.strip()
    selected = None

    for code, app in bot.apps.items():
        name = app.get("name", "")
        typed_prefix = f"@{name}"
        if content.lower().startswith(typed_prefix.lower()):
            selected = (code, app)
            user_text = content[len(typed_prefix):].strip()
            break

    if not selected:
        # If the user activated an app with /start talk, plain messages can talk to it.
        code = bot.active.get((message.guild.id, message.author.id))
        if code and code in bot.apps:
            selected = (code, bot.apps[code])
            user_text = content

    if selected and user_text:
        code, app = selected
        async with message.channel.typing():
            try:
                reply = await ai_reply(app, user_text, message.author.display_name)
                await message.reply(reply, mention_author=False)
            except Exception as e:
                print("AI error:", repr(e))
                await message.reply("Sorry, I couldn't reply right now.", mention_author=False)

    await bot.process_commands(message)

def run_bot():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing.")
    bot.run(token)
