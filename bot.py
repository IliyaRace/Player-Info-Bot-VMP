import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os
import requests
from functools import partial


DISCORD_BOT_TOKEN = "" # token Bot
OWNER_ID = 1329328987327037445 # id owner 
GUILD_ID = 1201116738696269836 # Id Server
ROLE_ID = 1201118709025091656 # Id Role Admin Bara Perm Bot

WHITELIST_FILE = "whitelist.json"
CHANNELS_FILE = "channels.json"
LICENSES_FILE = "licenses.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

whitelist = load_json(WHITELIST_FILE, [])
channels = load_json(CHANNELS_FILE, {})
licenses = load_json(LICENSES_FILE, {})

def save_licenses():
    save_json(LICENSES_FILE, licenses)


def has_license(user_id: int) -> bool:
    lic = licenses.get(str(user_id))
    if not lic:
        return False
    if not lic.get("active", False):
        return False
    allowed_until = lic.get("allowed_until")
    if not allowed_until:
        return False
    try:
        expire_date = datetime.strptime(allowed_until, "%Y-%m-%d")
    except Exception:
        return False
    return datetime.utcnow() <= expire_date

def is_channel_whitelisted(channel_id):
    return channel_id in whitelist
def parse_identifiers(identifiers):
    id_data = {}
    for identifier in identifiers:
        if identifier.startswith("steam:"):
            id_data["Steam"] = identifier.split(":")[1]
        elif identifier.startswith("license:"):
            if "License" not in id_data:
                id_data["License"] = identifier.split(":")[1]
            else:
                id_data["License2"] = identifier.split(":")[1]
        elif identifier.startswith("discord:"):
            id_data["Discord"] = identifier.split(":")[1]
        elif identifier.startswith("live:"):
            id_data["Live"] = identifier.split(":")[1]
        elif identifier.startswith("fivem:"):
            id_data["FiveM"] = identifier.split(":")[1]
    return id_data
@bot.command()
@commands.has_permissions(administrator=True)
async def addchannel(ctx, channel_id: int):
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ فقط مالک بات می‌تواند کانال به وایت‌لیست اضافه کند.")
        return

    if channel_id in whitelist:
        await ctx.send("⚠️ این کانال قبلاً به وایت‌لیست اضافه شده است.")
        return

    whitelist.append(channel_id)
    save_json(WHITELIST_FILE, whitelist)
    await ctx.send(f"✅ کانال <#{channel_id}> به وایت‌لیست اضافه شد.")

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    if not has_license(ctx.author.id) and ctx.author.id != OWNER_ID:
        await ctx.send("❌ شما لایسنس فعال ندارید.")
        return

    channels[str(ctx.guild.id)] = channel.id
    save_json(CHANNELS_FILE, channels)
    await ctx.send(f"✅ کانال <#{channel.id}> برای این سرور تنظیم شد.")
def fetch_country_code_for_ip(ip: str) -> str:
    """
    برمی‌گرداند کد کشور (مثل 'US' یا None) برای IP داده شده با استفاده از ipapi.co
    این تابع به صورت هم‌زمان نوشته شده چون قرار است در thread pool اجرا شود.
    """
    if not ip or ip in ["N/A", "127.0.0.1", "localhost"]:
        return None
    try:
        res = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
        if res.status_code == 200:
            data = res.json()
            country_code = data.get("country_code")
            if country_code:
                return country_code.upper()
    except Exception:
        pass
    return None

def country_code_to_flag(country_code: str) -> str:
    if not country_code:
        return "❓"
    return f":flag_{country_code.lower()}:"


@bot.command()
async def players(ctx):
    if not is_channel_whitelisted(ctx.channel.id):
        await ctx.send("❌ این کانال اجازه استفاده از دستور را ندارد.")
        return

    if not has_license(ctx.author.id):
        await ctx.send("❌ شما لایسنس فعال ندارید.")
        return

    players = get_vmp_players()
    if not players:
        await ctx.send("❌ هیچ بازیکنی متصل نیست.")
        return

    total = len(players)
    chunk_size = 10 
    loop = bot.loop

    for i in range(0, total, chunk_size):
        chunk = players[i:i + chunk_size]
        embed = discord.Embed(
            title="🟢 بازیکنان متصل",
            description=f"تعداد بازیکنان: **{total}** — صفحه {i//chunk_size + 1}",
            color=0x00FF00
        )

        for p in chunk:
            identifiers = p.get("identifiers", [])
            steam_hex = "N/A"
            for identifier in identifiers:
                if identifier.startswith("steam:"):
                    steam_hex = identifier.split(":")[1]
                    break


            ip = None
            for key in ["ip", "endpoint", "last_ip", "player_ip"]:
                val = p.get(key)
                if val:
                    ip = str(val).split(":")[0]
                    break
            if not ip:
                ip = "N/A"


            country_code = await loop.run_in_executor(None, partial(fetch_country_code_for_ip, ip))
            flag = country_code_to_flag(country_code)

            name_field = f"**Name:** {p.get('name', 'N/A')}\n**Steam Hex:** `{steam_hex}`"
            extra = f"ID: {p.get('id')} | Ping: {p.get('ping', 'N/A')} | IP: `{ip}`"
            embed.add_field(name=f"{flag} {extra}", value=name_field, inline=False)

        try:
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            await ctx.send(f"❌ خطا در ارسال لیست بازیکنان: {e}")
            return
@bot.command()
async def playerinfo(ctx, player_id: int):
    if not is_channel_whitelisted(ctx.channel.id):
        await ctx.send("❌ این کانال اجازه استفاده از دستور را ندارد.")
        return

    if not has_license(ctx.author.id):
        await ctx.send("❌ شما لایسنس فعال ندارید.")
        return

    channel_id = channels.get(str(ctx.guild.id))
    if channel_id is None:
        await ctx.send("❌ کانال برای این سرور تنظیم نشده است! لطفاً ابتدا دستور !setchannel را اجرا کنید.")
        return

    channel = bot.get_channel(channel_id)
    if channel is None:
        await ctx.send("❌ کانال تنظیم شده پیدا نشد.")
        return

    players = get_vmp_players() 
    player_data = next((p for p in players if p["id"] == player_id), None)

    if not player_data:
        await ctx.send(f"❌ بازیکنی با ID {player_id} پیدا نشد.")
        return

    id_data = parse_identifiers(player_data.get("identifiers", []))
    steam_name = player_data.get("name", "N/A")
    steam_hex = id_data.get("Steam", "N/A")
    player_info = get_player_job_and_gang(steam_hex)

    ip = None
    for key in ["ip", "endpoint", "last_ip", "player_ip"]:
        val = player_data.get(key)
        if val:
            ip = str(val).split(":")[0]
            break
    if ip is None:
        ip = "N/A"

    embed = discord.Embed(title=f"Player Info - ID: {player_data['id']}", color=0x00FFCC)
    embed.add_field(name="Steam Name", value=steam_name, inline=False)
    embed.add_field(name="Steam Hex", value=steam_hex, inline=False)
    embed.add_field(name="Ping", value=player_data.get("ping", "N/A"), inline=False)
    embed.add_field(name="IP", value=ip, inline=False)

    for key, value in id_data.items():
        if key != "Steam":
            embed.add_field(name=key, value=value, inline=False)

    # توجه: اگر get_player_job_and_gang نتایجی نداشت باید مطمئن بشی که ساختار dict برمی‌گردونه
    embed.add_field(name="Job", value=player_info.get("job", "N/A"), inline=True)
    embed.add_field(name="Job Grade", value=player_info.get("job_grade", "N/A"), inline=True)
    embed.add_field(name="Gang", value=player_info.get("gang", "N/A"), inline=True)
    embed.add_field(name="Gang Grade", value=player_info.get("gang_grade", "N/A"), inline=True)

    embed.set_footer(text="هر گونه باگ دیدید به ایدی refiqkhob اد بدید و پیام بدید")

    try:
        await channel.send(embed=embed)
        await ctx.send(f"✅ اطلاعات بازیکن در کانال <#{channel_id}> ارسال شد.")
    except discord.Forbidden:
        await ctx.send("❌ بات دسترسی ارسال پیام به کانال تنظیم شده را ندارد.")
    except discord.HTTPException as e:
        await ctx.send(f"❌ خطا در ارسال پیام به کانال: {e}")

# === دستورات لایسنس ===
@bot.group(invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def license(ctx):
    await ctx.send("دستورات لایسنس:\n`!license grant @user <days>` - دادن دسترسی\n`!license on` - فعال کردن دسترسی\n`!license status` - وضعیت لایسنس")

@license.command(name="grant")
@commands.has_permissions(administrator=True)
async def license_grant(ctx, user: discord.Member, days: int):
    if user.id == OWNER_ID:
        allowed_until = (datetime.utcnow() + timedelta(days=3650)).strftime("%Y-%m-%d") 
        licenses[str(user.id)] = {
            "allowed_until": allowed_until,
            "active": True
        }
        save_licenses()
        guild = bot.get_guild(GUILD_ID)
        if guild:
            role = guild.get_role(ROLE_ID)
            if role:
                try:
                    await user.add_roles(role)
                    await ctx.send(f"✅ دسترسی کامل و نامحدود به {user.mention} داده شد و رول اضافه شد.")
                    return
                except Exception:
                    pass
        await ctx.send(f"✅ دسترسی کامل و نامحدود به {user.mention} داده شد.")
        return

    if days < 1 or days > 10:
        await ctx.send("❌ تعداد روز باید بین 1 تا 10 باشد.")
        return

    allowed_until = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")
    licenses[str(user.id)] = {
        "allowed_until": allowed_until,
        "active": False
    }
    save_licenses()
    guild = bot.get_guild(GUILD_ID)
    if guild:
        role = guild.get_role(ROLE_ID)
        if role:
            try:
                await user.add_roles(role)
                await ctx.send(f"✅ دسترسی لایسنس برای {user.mention} تا تاریخ {allowed_until} داده شد و رول دسترسی اضافه شد. کاربر باید با `!license on` آن را فعال کند.")
                return
            except discord.Forbidden:
                await ctx.send("❌ بات دسترسی کافی برای اضافه کردن رول را ندارد.")
            except Exception as e:
                await ctx.send(f"❌ خطا هنگام اضافه کردن رول: {e}")
        else:
            await ctx.send("❌ رول دسترسی در سرور پیدا نشد.")
    else:
        await ctx.send("❌ سرور مشخص شده پیدا نشد.")

    await ctx.send(f"✅ دسترسی لایسنس برای {user.mention} تا تاریخ {allowed_until} داده شد. کاربر باید با `!license on` آن را فعال کند.")

@license.command(name="on")
async def license_on(ctx):
    user_id = str(ctx.author.id)
    lic = licenses.get(user_id)
    if not lic:
        await ctx.send("❌ شما لایسنس ندارید. ابتدا باید به شما دسترسی داده شود.")
        return

    if lic.get("active", False):
        await ctx.send("✅ لایسنس شما قبلاً فعال شده است.")
        return

    allowed_until = lic.get("allowed_until")
    if not allowed_until:
        await ctx.send("❌ تاریخ انقضا لایسنس شما مشخص نیست.")
        return

    try:
        expire_date = datetime.strptime(allowed_until, "%Y-%m-%d")
    except Exception:
        await ctx.send("❌ فرمت تاریخ لایسنس شما نامعتبر است.")
        return

    if datetime.utcnow() > expire_date:
        await ctx.send("❌ لایسنس شما منقضی شده است.")
        return

    licenses[user_id]["active"] = True
    save_licenses()

    guild = bot.get_guild(GUILD_ID)
    if guild:
        role = guild.get_role(ROLE_ID)
        member = guild.get_member(int(user_id))
        if role and member:
            try:
                await member.add_roles(role)
                await ctx.send("✅ لایسنس شما فعال شد و رول دسترسی به شما داده شد.")
                return
            except discord.Forbidden:
                await ctx.send("❌ بات دسترسی کافی برای اضافه کردن رول را ندارد.")
            except Exception as e:
                await ctx.send(f"❌ خطا هنگام اضافه کردن رول: {e}")
        else:
            await ctx.send("❌ نقش یا عضو در سرور پیدا نشد.")
    else:
        await ctx.send("❌ سرور مشخص شده پیدا نشد.")

@license.command(name="status")
async def license_status(ctx):
    user_id = str(ctx.author.id)
    lic = licenses.get(user_id)
    if not lic:
        await ctx.send("❌ شما لایسنس ندارید.")
        return

    allowed_until = lic.get("allowed_until")
    active = lic.get("active", False)
    await ctx.send(f"📝 وضعیت لایسنس شما:\nفعال: {'بله' if active else 'خیر'}\nتاریخ انقضا: {allowed_until}")


@bot.event
async def on_ready():
    print(f"بات با نام {bot.user} آماده است.")
from steam_players import get_player_job_and_gang
from vmp_players_with_ip import get_vmp_players

bot.run(DISCORD_BOT_TOKEN)

