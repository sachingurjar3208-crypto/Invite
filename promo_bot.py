import asyncio, json, os, re
import discord
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")  # token yaha hardcode mat karo
DELAY = 60  # seconds gap between each DM
DATA = "data.json"


def load():
    if os.path.exists(DATA):
        with open(DATA) as f:
            return json.load(f)
    return {"message": "Hello! Yaha announcement likho.", "optout": []}


def save():
    with open(DATA, "w") as f:
        json.dump(db, f)


db = load()
state = {"running": False, "stop": False, "sent": 0, "failed": 0, "total": 0}

intents = discord.Intents.default()
intents.members = True  # Dev Portal me "Server Members Intent" ON karo
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
OWNER_ID = 1317288099075850243


def owner_only(i: discord.Interaction) -> bool:
    return i.user.id == OWNER_ID


admin = app_commands.check(owner_only)


@tree.error
async def on_error(i: discord.Interaction, err: app_commands.AppCommandError):
    if isinstance(err, app_commands.CheckFailure):
        await i.response.send_message("⛔ Ye command sirf owner ke liye hai.", ephemeral=True)
    else:
        raise err


class EditModal(discord.ui.Modal, title="Edit Announcement"):
    text = discord.ui.TextInput(label="Message", style=discord.TextStyle.paragraph, max_length=2000)

    def __init__(self):
        super().__init__()
        self.text.default = db["message"]

    async def on_submit(self, i: discord.Interaction):
        db["message"] = str(self.text)
        save()
        await i.response.send_message("✅ Message updated.", ephemeral=True)


@tree.command(name="edit_message", description="Announcement message edit karo")
@admin
async def edit_message(i: discord.Interaction):
    await i.response.send_modal(EditModal())


@tree.command(name="preview", description="Current message dekho")
@admin
async def preview(i: discord.Interaction):
    await i.response.send_message(f"**Preview:**\n{db['message']}", ephemeral=True)


@tree.command(name="send_dm", description="UIDs ko 1 min gap me DM bhejo")
@app_commands.describe(uids="UIDs comma ya space se alag karke")
@admin
async def send_dm(i: discord.Interaction, uids: str):
    if state["running"]:
        return await i.response.send_message("⚠️ Ek job already chal raha hai.", ephemeral=True)
    ids = list(dict.fromkeys(int(x) for x in re.findall(r"\d{15,20}", uids)))
    ids = [u for u in ids if u not in db["optout"]]
    if not ids:
        return await i.response.send_message("Koi valid UID nahi mila.", ephemeral=True)
    state.update(running=True, stop=False, sent=0, failed=0, total=len(ids))
    await i.response.send_message(
        f"🚀 {len(ids)} users ko DM start. ETA ~{len(ids)*DELAY//60} min.", ephemeral=True)
    bot.loop.create_task(run_job(i.guild, i.user, ids))


async def run_job(guild, admin_user, ids):
    failed_ids = []
    for n, uid in enumerate(ids):
        if state["stop"]:
            break
        try:
            member = guild.get_member(uid) or await guild.fetch_member(uid)  # sirf server members
            await member.send(db["message"] + "\n\n-# Band karne ke liye /optout use karo")
            state["sent"] += 1
        except Exception:
            state["failed"] += 1
            failed_ids.append(uid)
        if n < len(ids) - 1:
            await asyncio.sleep(DELAY)
    state["running"] = False
    try:
        await admin_user.send(
            f"✅ Done. Sent: {state['sent']} | Failed: {state['failed']}\n"
            f"Failed IDs: {', '.join(map(str, failed_ids)) or 'none'}")
    except discord.HTTPException:
        pass


@tree.command(name="status", description="Job progress")
@admin
async def status(i: discord.Interaction):
    s = state
    await i.response.send_message(
        f"Running: {s['running']} | Sent {s['sent']}/{s['total']} | Failed {s['failed']}", ephemeral=True)


@tree.command(name="stop", description="Chal rahe job ko roko")
@admin
async def stop(i: discord.Interaction):
    state["stop"] = True
    await i.response.send_message("🛑 Stopping...", ephemeral=True)


@tree.command(name="optout", description="Promo DMs band karo")
async def optout(i: discord.Interaction):
    if i.user.id not in db["optout"]:
        db["optout"].append(i.user.id)
        save()
    await i.response.send_message("✅ Ab aapko promo DM nahi aayenge.", ephemeral=True)


@bot.event
async def on_ready():
    await tree.sync()
    print("Ready:", bot.user)


bot.run(TOKEN)
