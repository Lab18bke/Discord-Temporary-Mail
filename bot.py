import discord, asyncio, aioimaplib, email, random, string, json, os, time
from discord import app_commands


with open("config.json") as f:
    cfg = json.load(f)

TOKEN = cfg["token"]
MAIL_HOST = cfg["mail_host"]
MAIL_USER = cfg["mail_user"]
MAIL_PASS = cfg["mail_pass"]
DOMAIN = cfg["domain"]
ADMIN_ID = int(cfg["admin_id"])
GUILD_ID = int(cfg["guild_id"])
GUILD_OBJ = discord.Object(id=GUILD_ID)


ALIASES_FILE = "aliases.json"
STATS_FILE = "stats.json"


for file, default in [(ALIASES_FILE, {}), (STATS_FILE, {"generated": [], "emails": []})]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)

def load_json(file):
    with open(file) as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

def gen_alias():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))


intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)



@tree.command(name="temporarymail", description="Generate or reset your temporary email alias.", guilds=[GUILD_OBJ])
async def temporarymail(interaction: discord.Interaction):
    aliases = load_json(ALIASES_FILE)
    stats = load_json(STATS_FILE)
    uid = str(interaction.user.id)

 
    if uid in aliases:
        old_alias = aliases[uid]["alias"]
        try: await interaction.user.send(f"⚠️ Your previous alias `{old_alias}` has expired and been replaced.")
        except: pass

    new_alias = gen_alias() + "@" + DOMAIN
    aliases[uid] = {"alias": new_alias, "created": time.time()}
    save_json(ALIASES_FILE, aliases)

    stats["generated"].append(time.time())
    save_json(STATS_FILE, stats)

    await interaction.response.send_message(
        f"✅ Your new email alias is `{new_alias}`.\nAll emails sent to it will DM you here.\nThis alias will expire after 24 hours.",
        ephemeral=True
    )

@tree.command(name="summary", description="Show 24-hour usage summary (admin only).", guilds=[GUILD_OBJ])
async def summary(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ You can’t use this command.", ephemeral=True)
        return

    aliases = load_json(ALIASES_FILE)
    stats = load_json(STATS_FILE)
    cutoff = time.time() - 86400


    stats["generated"] = [t for t in stats.get("generated", []) if t > cutoff]
    stats["emails"] = [t for t in stats.get("emails", []) if t > cutoff]


    active_aliases = [a for a in aliases.values() if a["created"] > cutoff]

    save_json(STATS_FILE, stats)
    save_json(ALIASES_FILE, aliases)

    await interaction.response.send_message(
        f"📊 **Last 24 h Summary**\nActive aliases: **{len(active_aliases)}**\nEmails received: **{len(stats['emails'])}**",
        ephemeral=True
    )


async def check_unseen(client):
    typ, data_ids = await client.search("UNSEEN")
    if typ != "OK": return
    ids = data_ids[0].split()
    if not ids: return

    aliases = load_json(ALIASES_FILE)
    stats = load_json(STATS_FILE)

    for msgid in ids:
        _, msg_data = await client.fetch(msgid, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        from_addr = msg.get("From", "Unknown")
        subject = msg.get("Subject", "(no subject)")
        to_addr = msg.get("To", "")
        alias_name = to_addr.split("@")[0].lower()

    
        user_id = None
        for uid, info in aliases.items():
            if info["alias"].split("@")[0].lower() == alias_name:
                user_id = uid
                break
        if not user_id: continue


        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        user = bot.get_user(int(user_id))
        if user:
            try:
                await user.send(f"📩 **New Mail Received!**\n**From:** {from_addr}\n**Subject:** {subject}\n\n{body[:1800]}")
            except: pass


        stats["emails"].append(time.time())
        save_json(STATS_FILE, stats)

async def cleanup_aliases():
    while True:
        aliases = load_json(ALIASES_FILE)
        now = time.time()
        expired = [uid for uid, info in aliases.items() if now - info["created"] > 86400]
        for uid in expired:
            alias = aliases[uid]["alias"]
            user = bot.get_user(int(uid))
            if user:
                try: await user.send(f"⏰ Your previous alias `{alias}` has expired.")
                except: pass
            del aliases[uid]
        save_json(ALIASES_FILE, aliases)
        await asyncio.sleep(300) 

async def idle_loop():
    while True:
        try:
            client = aioimaplib.IMAP4_SSL(MAIL_HOST)
            await client.wait_hello_from_server()
            await client.login(MAIL_USER, MAIL_PASS)
            await client.select("INBOX")
            print("✅ IMAP connected, entering IDLE mode")

            while True:
                idle = await client.idle_start(timeout=None)
                await idle.wait()
                await client.idle_done()
                await check_unseen(client)
                await asyncio.sleep(1)
                await client.idle_start(timeout=None)
        except Exception as e:
            print("IMAP Error:", e)
            await asyncio.sleep(10)

@bot.event
async def on_ready():
    await tree.sync(guild=GUILD_OBJ)
    print(f"✅ Logged in as {bot.user} (Guild {GUILD_ID})")
    bot.loop.create_task(idle_loop())
    bot.loop.create_task(cleanup_aliases())

bot.run(TOKEN)
