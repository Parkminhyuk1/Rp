# full_bot_with_flask.py
# GH's BotShop - 정리된 단일 파일 버전 (Discord bot + Flask 통합)
# 작성자: ChatGPT (요청자: 토미11)
# 설명: 원본 스파게티 코드 정리. 중복된 Flask/IO 함수 통합, 비동기 요청 변경(aiohttp), 파일 입출력 유틸 정리.

import discord
from discord import app_commands
from discord.ext import commands
import random
import requests
import json
import time
from datetime import datetime, timedelta
from config import Config
import threading
import aiohttp
import os
import csv

# =========================
# 기본 설정 / 전역변수
# =========================
TOKEN = Config.bot_token
GUILD_ID = Config.guild_id
BLGROUP_ID = Config.blacklist_group_id
GROUP_ID = Config.group_id
fuckList = Config.censorship_message if hasattr(Config, "censorship_message") else []
# server_status는 전역에서 통일하여 사용 (open/special_mode 두 키를 가짐)
server_status = {"open": False, "special_mode": False}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# =========================
# 유틸: 파일 입출력 통합
# =========================
USER_DATA_FILE = "user_data.json"
CARS_DATA_FILE = "cars_data.json"
BAN_DATA_FILE = "ban_data.json"
SPECIAL_ACCESS_FILE = "special_access.json"
ALLOWED_PLAYERS_FILE = "allowed_players.json"
ACCESS_LOG_FILE = "access_log.txt"
VERIFICATION_LOG_FILE = "verification_logs.txt"
SEND_MONEY_LOG = "send_money.txt"
FORCED_TX_LOG = "forced_transactions.txt"

def load_json_file(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_user_data():
    return load_json_file(USER_DATA_FILE, {})

def save_user_data(data):
    save_json_file(USER_DATA_FILE, data)

def load_cars_data():
    return load_json_file(CARS_DATA_FILE, {})

def save_cars_data(data):
    save_json_file(CARS_DATA_FILE, data)

def load_ban_data():
    return load_json_file(BAN_DATA_FILE, {})

def save_ban_data(data):
    save_json_file(BAN_DATA_FILE, data)

def load_players(file_path):
    return load_json_file(file_path, [])

def save_players(file_path, data):
    save_json_file(file_path, data)

# 초기 캐시 로드 (필요 시 다시 파일에서 읽도록 구현)
special_access_players = load_players(SPECIAL_ACCESS_FILE)
allowed_players = load_players(ALLOWED_PLAYERS_FILE)

# =========================
# 로블록스 & 검증 관련 유틸
# =========================
user_cache = {}

def generate_verification_message():
    words = Config.verify_message if hasattr(Config, "verify_message") else ["verify_me"]
    return random.choice(words)

def get_user_id(username):
    if username in user_cache:
        return user_cache[username]
    try:
        resp = requests.get(f"https://users.roblox.com/v1/users/search?keyword={username}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and len(data["data"]) > 0:
                user_id = data["data"][0]["id"]
                user_cache[username] = user_id
                return user_id
    except Exception as e:
        print(f"[GH's BotShop] 유저 찾기 실패 : {e}")
    return None

def get_profile_description(user_id):
    try:
        resp = requests.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("description", "")
    except Exception as e:
        print(f"[GH's BotShop] 유저 프로필 설명란 찾기 실패 : {e}")
    return None

def is_in_blacklist_group(user_id, group_id):
    try:
        resp = requests.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for g in data.get("data", []):
                if g["group"]["id"] == group_id:
                    return True
    except Exception as e:
        print(f"[GH's BotShop] 유저 블랙그룹 찾기 실패 : {e}")
    return False

def is_in_group(user_id, group_id):
    try:
        resp = requests.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for g in data.get("data", []):
                if g["group"]["id"] == group_id:
                    return True
    except Exception as e:
        print(f"[GH's BotShop] 유저 그룹 찾기 실패: {e}")
    return False

def get_group_role(user_id, group_id):
    try:
        resp = requests.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for g in data.get("data", []):
                if g["group"]["id"] == group_id:
                    return g["role"]["name"]
    except Exception as e:
        print(f"[GH's BotShop] 그룹 역할 찾기 실패 : {e}")
    return None

def log_verification(status, username, user_id=None, reason=None):
    with open(VERIFICATION_LOG_FILE, "a", encoding="utf-8") as f:
        log_entry = f"[{datetime.now()}] 상태: {status} | 로블록스 닉네임: {username} | 아이디: {user_id} | 사유: {reason}\n"
        f.write(log_entry)
    print(log_entry)

# =========================
# Flask 통합 모듈
# =========================
from flask import Flask, jsonify, request
flask_app = Flask(__name__)

# latest call 안전하게 저장
_latest_call_lock = threading.Lock()
_latest_call = None

def log_access(username, allowed, mode):
    with open(ACCESS_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] 유져명: {username}, 허용여부: {allowed}, 모드: {mode}, 서버상태: {server_status}\n")

def notify_discord_money(discord_id, money):
    try:
        webhook_url = getattr(Config, "money_webhook_url", None)
        if webhook_url:
            message = f"<@{discord_id}> 님이 게임에 접속했습니다. 현재 보유 금액: {money}원"
            requests.post(webhook_url, json={"content": message}, timeout=5)
    except Exception:
        pass

@flask_app.route("/")
def home():
    return "Server is running!", 200

@flask_app.route("/api/users", methods=["GET"])
def api_get_all_users():
    return jsonify(load_user_data()), 200

@flask_app.route("/api/users/<string:roblox_nickname>", methods=["GET"])
def api_get_user_by_roblox(roblox_nickname):
    data = load_user_data()
    if roblox_nickname in data:
        return jsonify(data[roblox_nickname]), 200
    return jsonify({"error": "User not found"}), 404

@flask_app.route("/api/users", methods=["POST"])
def api_add_user():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    discord_user = data.get("discord_user")
    roblox_nickname = data.get("roblox_nickname")
    if not discord_user or not roblox_nickname:
        return jsonify({"error": "Missing fields"}), 400

    users = load_user_data()
    for uname, udata in users.items():
        if udata.get("roblox") == roblox_nickname:
            return jsonify({"error": "Roblox nickname already registered", "id": udata.get("id")}), 400
        if uname == discord_user:
            return jsonify({"error": "Discord user already registered", "id": udata.get("id")}), 400

    new_id = len(users) + 1
    users[discord_user] = {"roblox": roblox_nickname, "id": new_id, "money": 0, "License": "미보유"}
    save_user_data(users)
    return jsonify({"message": "User added", "id": new_id}), 201

@flask_app.route("/get_money/<string:roblox_nickname>", methods=["GET"])
def api_get_money(roblox_nickname):
    if not roblox_nickname:
        return jsonify({"error": "No username provided"}), 400
    users = load_user_data()
    money = users.get(roblox_nickname, {}).get("money", 0)
    discord_id = users.get(roblox_nickname, {}).get("id")
    if discord_id:
        notify_discord_money(discord_id, money)
    return jsonify({"money": money}), 200

@flask_app.route("/update_money", methods=["POST"])
def api_update_money():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    roblox_name = data.get("username")
    new_money = data.get("money")
    if not roblox_name or new_money is None:
        return jsonify({"error": "Invalid data"}), 400
    users = load_user_data()
    if roblox_name in users:
        users[roblox_name]["money"] = new_money
        save_user_data(users)
        return jsonify({"상태": "success"}), 200
    return jsonify({"error": "User not found"}), 404

@flask_app.route("/add_car", methods=["POST"])
def api_add_car():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    roblox_name = data.get("roblox_name")
    car_name = data.get("car_name")
    if not roblox_name or not car_name:
        return jsonify({"error": "Missing fields"}), 400

    cars = load_cars_data()
    while True:
        number_plate = f"{random.randint(100, 999)}{random.choice('가나다라마바사아자차카타파하')}{random.randint(1000, 9000)}"
        exists = any(car["number_plate"] == number_plate for cars_list in cars.values() for car in cars_list)
        if not exists:
            break

    cars.setdefault(roblox_name, []).append({"number_plate": number_plate, "car_name": car_name})
    save_cars_data(cars)
    return jsonify({"status": "success", "number_plate": number_plate}), 200

@flask_app.route("/remove_car", methods=["POST"])
def api_remove_car():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    number_plate = data.get("number_plate")
    if not number_plate:
        return jsonify({"error": "Missing number_plate"}), 400

    cars = load_cars_data()
    owner = None
    for name, car_list in cars.items():
        for car in list(car_list):
            if car.get("number_plate") == number_plate:
                car_list.remove(car)
                owner = name
                break
        if owner:
            break

    if not owner:
        return jsonify({"상태": "error", "사유": "번호판을 찾을 수 없습니다."}), 404

    save_cars_data(cars)
    return jsonify({"status": "success", "owner": owner}), 200

@flask_app.route("/get_cars", methods=["GET"])
def api_get_cars():
    roblox_name = request.args.get("roblox_name")
    if not roblox_name:
        return jsonify({"error": "Missing roblox_name"}), 400
    cars = load_cars_data()
    if roblox_name not in cars:
        return jsonify({"상태": "error", "사유": "차량이 없습니다."}), 404
    return jsonify({"status": "success", "cars": cars[roblox_name]}), 200

@flask_app.route("/ban_data", methods=["GET"])
def api_get_ban_data():
    return jsonify(load_ban_data()), 200

@flask_app.route("/check_player", methods=["POST"])
def api_check_player():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    roblox_username = data.get("username")
    if not roblox_username:
        return jsonify({"error": "Username is required"}), 400

    if server_status.get("special_mode", False):
        allowed = roblox_username in load_players(SPECIAL_ACCESS_FILE)
        log_access(roblox_username, allowed, "special_mode")
        return jsonify({"allowed": allowed}), 200

    if not server_status.get("open", False):
        allowed = roblox_username in load_players(ALLOWED_PLAYERS_FILE)
        log_access(roblox_username, allowed, "closed_server")
        return jsonify({"allowed": allowed}), 200

    log_access(roblox_username, True, "open_server")
    return jsonify({"allowed": True}), 200

@flask_app.route("/receive_call", methods=["POST"])
def api_receive_call():
    global _latest_call
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    call = {
        "team": data.get("team"),
        "caller": data.get("caller"),
        "caller_id": data.get("caller_id"),
        "location": data.get("location"),
        "reason": data.get("reason"),
        "timestamp": datetime.now().isoformat()
    }
    with _latest_call_lock:
        _latest_call = call
    return jsonify({"status": "success"}), 200

@flask_app.route("/get_call", methods=["GET"])
def api_get_call():
    global _latest_call
    with _latest_call_lock:
        if _latest_call:
            call_copy = _latest_call.copy()
            _latest_call = None
            return jsonify(call_copy), 200
    return jsonify({"status": "no_call"}), 200

# =========================
# Discord Bot 설정
# =========================
class VerifyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!!!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)
        print("GH's BotShop - Slash commands synced")

bot = VerifyBot()

@bot.event
async def on_ready():
    print(f"[GH's BotShop] Bot ready as {bot.user} (latency: {round(bot.latency*1000)}ms)")
    # 상태 설정
    try:
        if Config.status_type == 0:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"{Config.status_message}"))
        elif Config.status_type == 1:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.streaming, name=f"{Config.status_message}"))
        elif Config.status_type == 2:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"{Config.status_message}"))
        elif Config.status_type == 3:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{Config.status_message}"))
    except Exception as e:
        print(f"[GH's BotShop] 상태 설정 중 오류: {e}")

@bot.event
async def on_member_join(member):
    join_message = f"{Config.server_name}에 오신것을 환영합니다, {member.mention}님!"
    embed = discord.Embed(title=":wave:ㆍ반가워요!", description=join_message, color=0x00ff00)
    embed.add_field(name=":date:  입국 날짜", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name=":id:  디스코드 ID", value=member.id, inline=False)
    embed.add_field(name=":name_badge:  닉네임", value=member.display_name, inline=False)
    try:
        await member.send(embed=embed)
    except discord.errors.HTTPException:
        print(f"[GH's BotShop] 유저에게 DM 전송 실패 : {member.display_name}.")
    # 채널 기록
    log_channel = bot.get_channel(Config.join_channel_id) if hasattr(Config, "join_channel_id") else None
    if log_channel:
        join_embed = discord.Embed(title="EMOJI_0ㆍ입국확인표", color=0x00ff00)
        join_embed.add_field(name=":name_badge:  닉네임", value=f"{member.mention} ({member.display_name})", inline=False)
        join_embed.add_field(name=":id:  디스코드 ID", value=member.id, inline=False)
        join_embed.add_field(name=":date:  입국 날짜", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        await log_channel.send(embed=join_embed)

@bot.event
async def on_member_remove(member):
    log_channel = bot.get_channel(Config.leave_channel_id) if hasattr(Config, "leave_channel_id") else None
    if log_channel:
        leave_embed = discord.Embed(title="EMOJI_1ㆍ출국확인표", color=0xff0000)
        leave_embed.add_field(name=":name_badge: 닉네임", value=f"{member.mention} ({member.display_name})", inline=False)
        leave_embed.add_field(name=":id: 디스코드 ID", value=member.id, inline=False)
        leave_embed.add_field(name=":date: 출국 날짜", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        await log_channel.send(embed=leave_embed)

# 인증 버튼 뷰
class VerifyButton(discord.ui.View):
    def __init__(self, interaction, user_id, username, verification_message):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.user_id = user_id
        self.username = username
        self.verification_message = verification_message

    @discord.ui.button(label="인증 확인", style=discord.ButtonStyle.green)
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("이 버튼은 다른 사용자를 위한 것입니다.", ephemeral=True)
            return

        description = get_profile_description(self.user_id)
        if description == self.verification_message:
            try:
                group_role_name = get_group_role(self.user_id, GROUP_ID)
                if not group_role_name:
                    embed = discord.Embed(title="인증 실패", description="그룹 역할 정보를 가져올 수 없습니다.", color=discord.Color.red())
                    await self.interaction.edit_original_response(embed=embed, view=None)
                    log_verification("Failed", self.username, user_id=self.user_id, reason="No group role found")
                    return

                role_mapping = getattr(Config, "role_mapping", {})
                nick_mapping = getattr(Config, "nick_mapping", {})

                discord_role_name = role_mapping.get(group_role_name)
                discord_nick_form = nick_mapping.get(group_role_name)

                if discord_role_name:
                    guild = interaction.guild
                    discord_role = discord.utils.get(guild.roles, name=discord_role_name)

                    if discord_role:
                        await interaction.user.add_roles(discord_role)
                        embed = discord.Embed(
                            title="인증 성공",
                            description=f"로블록스 계정 `{self.username}` 인증이 완료되었습니다!\n-# 지급된 역할: `{discord_role_name}`",
                            color=discord.Color.green()
                        )
                        await self.interaction.edit_original_response(embed=embed, view=None)
                        log_verification("Success", self.username, user_id=self.user_id, reason=f"지급된 역할: {discord_role_name}")

                        # 이미 같은 로블록스 닉네임이 등록된 경우
                        users = load_user_data()
                        if self.username in users:
                            return

                        new_unique_id = len(users) + 1
                        users[self.username] = {"discord": interaction.user.name, "id": new_unique_id, "money": 0, "License": 0}
                        save_user_data(users)

                        new_nickname = getattr(Config, "nick_form", f"{new_unique_id}ㆍ{self.username}")
                        try:
                            await interaction.user.edit(nick=new_nickname)
                        except Exception:
                            pass

                        embed = discord.Embed(
                            title="인증 성공",
                            description=f"로블록스 계정 `{self.username}` 인증이 완료되었습니다!\n-# 지급된 역할: `{discord_role_name}` / 발급된 고유번호 : `{new_unique_id}`",
                            color=discord.Color.green()
                        )
                        await self.interaction.edit_original_response(embed=embed, view=None)
                        return
                    else:
                        raise Exception(f"Role `{discord_role_name}` not found in Discord")
                else:
                    embed = discord.Embed(title="인증 실패", description="매핑된 Discord 역할이 없습니다. 관리자에게 문의하세요.", color=discord.Color.red())
                    await self.interaction.edit_original_response(embed=embed, view=None)
                    log_verification("Failed", self.username, user_id=self.user_id, reason="역할이 맵핑되어있지 않음.")
            except Exception as e:
                embed = discord.Embed(title="인증 실패", description=f"인증은 성공했지만 추가 작업 중 오류가 발생했습니다: {str(e)}", color=discord.Color.red())
                await self.interaction.edit_original_response(embed=embed, view=None)
                log_verification("Failed", self.username, user_id=self.user_id, reason=str(e))
        else:
            embed = discord.Embed(title="인증 실패", description="프로필 소개 문구가 올바르지 않습니다.", color=discord.Color.red())
            await self.interaction.edit_original_response(embed=embed, view=None)
            log_verification("Failed", self.username, user_id=self.user_id, reason="소개 문구 불일치")

# 인증 명령어
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="인증", description="로블록스 계정을 인증합니다.")
async def verify(interaction: discord.Interaction, username: str):
    users = load_user_data()
    user_id = get_user_id(username)
    if not user_id:
        embed = discord.Embed(title="인증 실패", description="사용자를 찾을 수 없습니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        log_verification("Failed", username, reason="유저를 찾지 못함.")
        return

    if is_in_blacklist_group(user_id, BLGROUP_ID):
        embed = discord.Embed(title="인증 실패", description="해당 그룹에 가입된 사용자는 인증할 수 없습니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        log_verification("Failed", username, user_id=user_id, reason="블랙리스트 그룹에 가입되어있음.")
        return

    if not is_in_group(user_id, GROUP_ID):
        embed = discord.Embed(title="인증 실패", description=f"[해당 그룹에 가입된 사용자만 인증할 수 있습니다. (이 메시지 클릭)](https://www.roblox.com/ko/communities/{Config.group_id})", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        log_verification("Failed", username, user_id=user_id, reason="그룹에 가입되어 있지 않음.")
        return

    verification_message = generate_verification_message()
    embed = discord.Embed(
        title="인증 요청",
        description=f"로블록스 프로필 소개 문구를 아래와 같이 변경해주세요:\n`{verification_message}`\n\n변경 후 아래 버튼을 눌러 인증을 완료하세요.",
        color=discord.Color.blue(),
    )
    view = VerifyButton(interaction, user_id, username, verification_message)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="핑", description="봇의 핑을 확인합니다.")
async def 핑(interaction: discord.Interaction):
    embed = discord.Embed(title="EMOJI_2ㆍ퐁!!", description=f'{round(bot.latency * 1000)}ms 걸림!!', color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

# =========================
# 호출 명령어: requests -> aiohttp 비동기 사용
# =========================
ROLE_MAPPING = getattr(Config, "call_role_mapping", {})

@bot.tree.command(guild=discord.Object(id=Config.guild_id), name="호출", description="특정 역할을 호출하여 DM 및 로블록스에 알림을 보냅니다.")
@app_commands.describe(role="호출할 역할 선택", location="사건이 발생한 위치", reason="호출 사유")
async def call_command(interaction: discord.Interaction, role: str, location: str, reason: str):
    users = load_user_data()
    if role not in ROLE_MAPPING:
        embed = discord.Embed(title=f"{Config.blocked_emoji}ㆍ호출 실패", description="잘못된 역할입니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    guild = interaction.guild
    role_obj = guild.get_role(ROLE_MAPPING[role])
    if not role_obj:
        embed = discord.Embed(title=f"{Config.blocked_emoji}ㆍ호출 실패", description="역할 맵핑 실패됨. 관리자를 호출해주세요!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    caller = interaction.user
    message_content = discord.Embed(title="호출 알림", description=f"- 요청자: {caller.display_name}({caller.id})\n- 장소: {location}\n- 사유: {reason}")
    for member in role_obj.members:
        try:
            await member.send(embed=message_content)
        except:
            pass

    roblox_payload = {
        "team": role,
        "caller": caller.display_name,
        "caller_id": str(caller.id),
        "location": location,
        "reason": reason
    }

    # 비동기 POST (로컬 Flask)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://127.0.0.1:{Config.server_port}/receive_call", json=roblox_payload, timeout=5) as resp:
                if resp.status != 200:
                    raise Exception(f"status {resp.status}")
    except Exception as e:
        embed = discord.Embed(title=f"{Config.blocked_emoji}ㆍ호출 실패", description=f"로블록스 서버로 알림을 전송하지 못했습니다.\n에러 내용 : {e}", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(title=f"{Config.success_emoji}ㆍ호출 성공", description=f"{role}에게 호출 알림을 보냈습니다.", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@call_command.autocomplete("role")
async def role_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=r, value=r) for r in ROLE_MAPPING.keys() if current.lower() in r.lower()]

# =========================
# 유저정보 조회, 송금 등
# =========================
def log_transaction(sender, recipient, amount, success=True, reason=None):
    with open(SEND_MONEY_LOG, "a", encoding="utf-8") as f:
        if success:
            f.write(f"[{datetime.now()}] 성공: {sender} -> {recipient}: {amount}원\n")
        else:
            f.write(f"[{datetime.now()}] 실패: {sender} -> {recipient}: {amount}원 | 사유: {reason}\n")

def find_roblox_nickname_by_discord_name(user_data, discord_name):
    for roblox_nickname, data in user_data.items():
        if data["discord"] == discord_name:
            return roblox_nickname
    return None

@bot.tree.command(guild=discord.Object(GUILD_ID), name="송금", description="다른 유저에게 돈을 송금합니다.")
@app_commands.describe(recipient="돈을 받을 유저를 선택하세요.", amount="송금할 금액을 입력하세요.")
async def send_money(interaction: discord.Interaction, recipient: discord.Member, amount: int):
    sender_discord = interaction.user.name
    recipient_discord = recipient.name

    if amount <= 0:
        log_transaction(sender_discord, recipient_discord, amount, success=False, reason="금액이 0 이하")
        embed = discord.Embed(title=f"{Config.blocked_emoji}ㆍ송금 실패", description=f"송금할 금액이 0원 이하입니다.\n-# 송금 시도액 : {amount}", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    users = load_user_data()
    sender_roblox = find_roblox_nickname_by_discord_name(users, sender_discord)
    recipient_roblox = find_roblox_nickname_by_discord_name(users, recipient_discord)

    if sender_roblox is None:
        log_transaction(sender_discord, recipient_discord, amount, success=False, reason="송금자 정보 없음")
        embed = discord.Embed(title=f"{Config.blocked_emoji}ㆍ송금 실패", description="당신의 정보가 없습니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    if recipient_roblox is None:
        log_transaction(sender_discord, recipient_discord, amount, success=False, reason="수령자 정보 없음")
        embed = discord.Embed(title=f"{Config.blocked_emoji}ㆍ송금 실패", description="받을 사람의 정보가 없습니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    sender_data = users[sender_roblox]
    recipient_data = users[recipient_roblox]

    if sender_data.get("money", 0) < amount:
        log_transaction(sender_discord, recipient_discord, amount, success=False, reason="잔액 부족")
        embed = discord.Embed(title=f"{Config.blocked_emoji}ㆍ송금 실패", description=f"송금할 금액이 부족합니다! \n-# 현재 보유 금액 : {sender_data.get('money', 0)}\n-# 송금 시도액 : {amount}", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    sender_data["money"] = sender_data.get("money", 0) - amount
    recipient_data["money"] = recipient_data.get("money", 0) + amount
    save_user_data(users)
    log_transaction(sender_data["discord"], recipient_data["discord"], amount, success=True)

    embed = discord.Embed(title=f"{Config.success_emoji}ㆍ송금 성공!", description=f"{recipient.mention}님에게 {amount}원을 성공적으로 송금했습니다!", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(guild=discord.Object(GUILD_ID), name="유저정보_확인", description="저장된 유저 정보를 확인합니다.")
@app_commands.describe(discord_user="디스코드 유저 선택")
async def check_user_info(interaction: discord.Interaction, discord_user: discord.User):
    users = load_user_data()
    roblox_names = [nickname for nickname, data in users.items() if data.get("discord") == discord_user.name]

    if not roblox_names:
        await interaction.response.send_message(embed=discord.Embed(title="유저 정보 없음", description=f"{discord_user.name}님은 등록된 정보가 없습니다.", color=discord.Color.red()))
        return

    embed = discord.Embed(title=f"{discord_user.name}님의 유저 정보", color=discord.Color.blue())
    embed.set_thumbnail(url=discord_user.avatar.url if discord_user.avatar else None)

    for roblox_name in roblox_names:
        user_info = users[roblox_name]
        money = user_info.get("money", 0)
        embed.add_field(name=f"EMOJI_3 로블록스 닉네임: {roblox_name}",
                        value=(f"- 고유번호: `{user_info.get('id')}`\n- 보유 금액: `{money} 원`\n- 면허 종류: `{user_info.get('License')}`"),
                        inline=False)

    await interaction.response.send_message(embed=embed)

# =========================
# on_message 이벤트 (명령어: prefix 기반)
# =========================
def log_forced_transaction(sender_id, receiver_id, amount, status):
    with open(FORCED_TX_LOG, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] 전송자: {sender_id}, 수령자: {receiver_id}, 금액: {amount}, 상태: {status}\n")

@bot.event
async def on_message(message):
    # 기본 처리(명령어 등) 전에 봇 자신의 메시지는 무시
    if message.author == bot.user:
        return

    content = message.content.strip()

    # !도움말 예시
    if content == "!도움말":
        if not any(role.id == getattr(Config, "help_id", -1) for role in message.author.roles):
            await message.channel.send(embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red()))
            return
        embed = discord.Embed(title="도움말", description="명령어 목록:", color=discord.Color.blue())
        embed.add_field(name="!상태변경", value="봇 상태 변경", inline=False)
        embed.add_field(name="!강제송금", value="강제송금", inline=False)
        embed.add_field(name="!고유번호 발급/삭제/변경", value="고유번호 관리", inline=False)
        embed.add_field(name="!서버온 / !서버오프 / !특수접속", value="서버 상태 변경", inline=False)
        embed.add_field(name="!특수추가 / !특수확인", value="특수접속 리스트 관리", inline=False)
        embed.add_field(name="!면허지급 / !면허회수", value="면허 지급/회수", inline=False)
        embed.add_field(name="!차량회수", value="차량 회수", inline=False)
        embed.add_field(name="!밴", value="유저 밴", inline=False)
        embed.add_field(name="!돈 지급/회수", value="돈 지급/회수", inline=False)
        await message.channel.send(embed=embed)
        return

    # 간단한 권한 기반 명령어 예시: !서버온, !서버오프, !특수접속
    if content == "!서버온":
        if any(role.id == getattr(Config, "server_manager_id", -1) for role in message.author.roles):
            server_status["open"] = True
            embed = discord.Embed(title=f"{getattr(Config, 'server_on', '서버 활성화')}ㆍ서버 활성화", description=f"{getattr(Config, 'serveron_message', '')}", color=discord.Color.blue())
            button = discord.ui.Button(label="⏩ 들어가기", url=f"https://www.roblox.com/ko/games/{getattr(Config, 'place_id', '')}")
            view = discord.ui.View()
            view.add_item(button)
            await message.channel.send(embed=embed, view=view)
            try:
                await message.delete()
            except:
                pass
        else:
            await message.channel.send(embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red()))
        return

    if content == "!서버오프":
        if any(role.id == getattr(Config, "server_manager_id", -1) for role in message.author.roles):
            server_status["open"] = False
            embed = discord.Embed(title=f"{getattr(Config, 'server_off', '서버 비활성화')}ㆍ서버 비활성화", description=f"{getattr(Config, 'serveroff_message', '')}", color=discord.Color.red())
            await message.channel.send(embed=embed)
            try:
                await message.delete()
            except:
                pass
        else:
            await message.channel.send(embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red()))
        return

    if content == "!특수접속":
        if any(role.id == getattr(Config, "server_manager_id", -1) for role in message.author.roles):
            server_status["special_mode"] = True
            embed = discord.Embed(title=f"{getattr(Config, 'special_access', '특수접속')}ㆍ특수접속", description=f"{getattr(Config, 'special_message', '')}", color=discord.Color.yellow())
            button = discord.ui.Button(label="⏩ 들어가기", url=f"https://www.roblox.com/ko/games/{getattr(Config, 'place_id', '')}")
            view = discord.ui.View()
            view.add_item(button)
            await message.channel.send(embed=embed, view=view)
            try:
                await message.delete()
            except:
                pass
        else:
            await message.channel.send(embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red()))
        return

    # !특수추가 [닉네임]
    if content.startswith("!특수추가"):
        if any(role.id == getattr(Config, "server_manager_id", -1) for role in message.author.roles):
            parts = content.split(" ", 1)
            if len(parts) < 2 or not parts[1].strip():
                await message.channel.send(embed=discord.Embed(title="작동 실패", description="사용자명을 입력해주세요. 예: `!특수추가 [로블록스 닉네임]`", color=discord.Color.red()))
                return
            roblox_username = parts[1].strip()
            if roblox_username not in special_access_players:
                special_access_players.append(roblox_username)
                save_players(SPECIAL_ACCESS_FILE, special_access_players)
                await message.channel.send(embed=discord.Embed(title="추가 성공", description=f"{roblox_username}님이 특수 접속 리스트에 추가되었습니다!", color=discord.Color.green()))
            else:
                await message.channel.send(embed=discord.Embed(title="작동 실패", description=f"{roblox_username}님은 이미 특수 접속 리스트에 있습니다.", color=discord.Color.red()))
        else:
            await message.channel.send(embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red()))
        return

    if content == "!특수확인":
        if special_access_players:
            await message.channel.send(embed=discord.Embed(title="특수 접속 허용자 목록", description="\n".join(special_access_players), color=discord.Color.blue()))
        else:
            await message.channel.send(embed=discord.Embed(title="작동 실패", description="현재 특수 접속 허용자 리스트가 비어 있습니다.", color=discord.Color.red()))
        return

    # 차량 회수: !차량회수 <번호판>
    if content.startswith("!차량회수"):
        if any(role.id == getattr(Config, "car_steal_id", -1) for role in message.author.roles):
            parts = content.split(" ", 1)
            if len(parts) < 2 or not parts[1].strip():
                await message.channel.send(embed=discord.Embed(title="작동 실패", description="사용방법 : `!차량회수 [번호판]`", color=discord.Color.red()))
                return
            number_plate = parts[1].strip()
            cars = load_cars_data()
            owner = None
            for name, car_list in cars.items():
                for car in list(car_list):
                    if car.get("number_plate") == number_plate:
                        car_list.remove(car)
                        owner = name
                        break
                if owner:
                    break
            if not owner:
                await message.channel.send(embed=discord.Embed(title="작동 실패", description="해당 번호판에 해당하는 차량이 없습니다.", color=discord.Color.red()))
            else:
                save_cars_data(cars)
                await message.channel.send(embed=discord.Embed(title="회수 성공", description=f"차량 {number_plate}이(가) 회수되었습니다.", color=discord.Color.green()))
        else:
            await message.channel.send(embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red()))
        return

    # 금지어 필터링
    for kw in fuckList:
        if kw in content:
            guild = bot.get_guild(GUILD_ID)
            member = guild.get_member(message.author.id) if guild else None
            await message.channel.send(embed=discord.Embed(title=f"{Config.blocked_emoji}ㆍ검열됨!", description=f"{message.author}님께서 욕설을 사용하셨습니다!\n타임아웃 1분이 지급되었습니다.", color=discord.Color.red()))
            try:
                await message.delete()
            except:
                pass
            if member:
                try:
                    await member.timeout(timedelta(minutes=1), reason=f"욕설 사용 (메시지 : {content})")
                except Exception:
                    pass
            break

 # 유저 데이터 로드

        user_data = load_data()



        if roblox_nickname not in user_data:

            embed=discord.Embed(title="작동 실패", description=f"로블록스 닉네임 `{roblox_nickname}` 을(를) 찾을 수 없습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return



        if user_data[roblox_nickname]["License"] == "미보유":

            embed=discord.Embed(title="작동 실패", description=f"`{roblox_nickname}` 님은 면허를 보유하고 있지 않습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return



        # 면허 회수수 수퍼노바 사건은 다가와 오오예

        user_data[roblox_nickname]["License"] = "미보유"

        save_data(user_data)



        # Discord 사용자 검색

        discord_username = user_data[roblox_nickname]["discord"]  # 사용자명

        member = discord.utils.get(message.guild.members, name=discord_username)



        if member:

            try:

                embed = discord.Embed(title="면허 회수됨", description=f"{roblox_nickname}님께서부터 면허가 회수되었습니다.", color=discord.Color.red())

                await member.send(embed=embed)

                embed=discord.Embed(title="면허 회수 성공", description=f"`{roblox_nickname}` 님에게 면허를 성공적으로 회수했습니다.", color=discord.Color.green())

                await message.channel.send(embed=embed)

            except discord.Forbidden:

                embed=discord.Embed(title="면허 회수 성공", description=f"`{roblox_nickname}` 님에게 면허를 회수했지만 DM을 보낼 수 없습니다.", color=discord.Color.yellow())

                await message.channel.send(embed)

        else:

            embed=discord.Embed(title="작동 실패", description=f"서버에서 `{roblox_nickname}` 님을 찾을 수 없습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)

    if message.content.startswith("!밴"):

        user_data = load_data()

        if not any(role.id == Config.ban_role for role in message.author.roles):

            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return

        

        args = message.content.split(" ", 3)

        if len(args) < 4:

            embed=discord.Embed(title="작동 실패", description=f"사용방법 : `!밴 [로블록스 닉네임] [디스코드 사용자명] [사유]`", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return

        

        roblox_name, discord_name, reason = args[1], args[2], args[3]

        

        # 대상 디스코드 유저 찾기

        member = discord.utils.get(message.guild.members, name=discord_name)

        if member is None:

            embed=discord.Embed(title="작동 실패", description="해당 디스코드 사용자를 찾을 수 없습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return

        

        # 디스코드에서 밴

        try:

            await message.guild.ban(member, reason=reason)

        except discord.Forbidden:

            embed=discord.Embed(title="작동 실패", description="권한이 부족하여 밴할 수 없습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return



        # 밴 데이터 저장

        ban_data = load_ban_data()

        ban_data[roblox_name] = {

            "discord": discord_name,

            "discord_id": member.id,

            "reason": reason

        }

        save_ban_data(ban_data)

        embed=discord.Embed(title="밴 성공", description=f"{roblox_name}({discord_name})을(를) 밴했습니다.\n-# 사유: {reason}", color=discord.Color.green())

        await message.channel.send(embed=embed)

    if message.content.startswith("!고유번호 변경"):

        parts = message.content.split(" ")

        user_data = load_data()

        if not any(role.id == Config.ID_manage_id for role in message.author.roles):

            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return

        if len(parts) != 4:

            embed=discord.Embed(title="작동 실패", description=f"사용방법 : `!고유번호 변경 [디스코드 사용자명] [새로운 고유번호]`", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return



        discord_user = parts[2]

        new_id = parts[3]



        if discord_user in user_data:

            user_data[discord_user]["id"] = new_id

            save_data(user_data)

            embed=discord.Embed(title="변경 성공", description=f"{discord_user}님의 고유번호가 {new_id}(으)로 변경되었습니다.", color=discord.Color.green())

            await message.channel.send(embed=embed)

        else:

            embed=discord.Embed(title="작동 실패", description=f"{discord_user}님은 등록되지 않았습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)



    # 돈 지급

    if message.content.startswith("!돈 지급"):

        parts = message.content.split()

        user_data = load_data()

        if not any(role.id == Config.money_manage_id for role in message.author.roles):

            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return

        if len(parts) != 4:

            embed=discord.Embed(title="작동 실패", description=f"사용방법 : `!돈 지급 [로블록스 닉네임] [금액]`", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return



        discord_user = parts[2]

        amount = int(parts[3])



        if discord_user in user_data:

            user_data[discord_user]["money"] = user_data[discord_user].get("money", 0) + amount

            save_data(user_data)

            embed=discord.Embed(title="지급 성공", description=f"{discord_user}님께 {amount}원이 지급되었습니다. \n-# {discord_user}님의 현재 잔액: {user_data[discord_user]['money']}원", color=discord.Color.green())

            await message.channel.send(embed=embed)

        else:

            embed=discord.Embed(title="작동 실패", description=f"{discord_user}님은 등록되지 않았습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)



    # 돈 회수

    if message.content.startswith("!돈 회수"):

        parts = message.content.split()

        user_data = load_data()

        if not any(role.id == Config.money_manage_id for role in message.author.roles):

            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return

        if len(parts) != 4:

            embed=discord.Embed(title="작동 실패", description=f"사용방법 : `!돈 회수 [로블록스 닉네임] [금액]`", color=discord.Color.red())

            await message.channel.send(embed=embed)

            return



        discord_user = parts[2]

        amount = int(parts[3])



        if discord_user in user_data:

            user_data[discord_user]["money"] = max(0, user_data[discord_user].get("money", 0) - amount)

            save_data(user_data)

            embed=discord.Embed(title="지급 성공", description=f"{discord_user}님께 {amount}원이 회수되었습니다. \n-# {discord_user}님의 현재 잔액: {user_data[discord_user]['money']}원", color=discord.Color.green())

            await message.channel.send(embed=embed)

        else:

            embed=discord.Embed(title="작동 실패", description=f"{discord_user}님은 등록되지 않았습니다.", color=discord.Color.red())

            await message.channel.send(embed=embed)


# =========================
# 앱 실행 (Flask 스레드 + Discord run)
# =========================
def run_flask():
    flask_app.run(host="0.0.0.0", port=getattr(Config, "server_port", 5000), threaded=True)

if __name__ == "__main__":
    # Flask 스레드 시작 (데몬으로 실행)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("[GH's BotShop] Flask 서버 시작됨")

    # Discord 봇 실행
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"[SYSTEM] 봇 실행 중 오류: {e}")
