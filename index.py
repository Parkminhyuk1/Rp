#█▀▀▀ █░░█ █▀▀ █░░█ █▀▀█ █▀▀█
#█░▀█ █▀▀█ ▀▀█ █▀▀█ █░░█ █░░█
#▀▀▀▀ ▀░░▀ ▀▀▀ ▀░░▀ ▀▀▀▀ █▀▀▀

# 모든 내용은 챗지피티와 같이 만듬. 코드가 스파게티마냥 꼬여있습니다. 알아서 풀어서 쓰시길..
# 문제 있어도 연락하지 마요. 알아서 고쳐서 써요.

import discord
from discord import app_commands
from discord.ext import commands
import random
import requests
import json
import time
from datetime import datetime
from config import Config
import threading
import aiohttp
import os
import csv

def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # Flask 서버를 별도의 스레드로 실행 (Koyeb 헬스체크용)
    threading.Thread(target=run_flask, daemon=True).start()
    print("[GH's BotShop] Flask 서버가 백그라운드에서 실행 중입니다.")

# 봇 설정
TOKEN = Config.bot_token
GUILD_ID = Config.guild_id
BLGROUP_ID = Config.blacklist_group_id
GROUP_ID = Config.group_id
fuckList = Config.censorship_message
server_status = {"open": False}
server_status = {"special_mode": False}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
client = discord.Client(intents=intents)

# 인증 문구 생성 (랜덤)
def generate_verification_message():
    words = Config.verify_message #인증시 사용할 문구들
    return random.choice(words)

# 사용자 데이터를 저장하는 캐시
user_cache = {}

# 로블록스 사용자 정보 가져오기
def get_user_id(username):
    # 캐시에 있는지 확인
    if username in user_cache:
        return user_cache[username]
    
    try:
        response = requests.get(f"https://users.roblox.com/v1/users/search?keyword={username}")
        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                user_id = data["data"][0]["id"]
                user_cache[username] = user_id  # 캐시에 저장
                return user_id
    except Exception as e:
        print(f"[GH's BotShop] 유저 찾기 실패 : {e}")
    return None

# 사용자 프로필 소개글 가져오기
def get_profile_description(user_id):
    try:
        response = requests.get(f"https://users.roblox.com/v1/users/{user_id}")
        if response.status_code == 200:
            data = response.json()
            return data.get("description", "")
    except Exception as e:
        print(f"[GH's BotShop] 유저 프로필 설명란 찾기 실패 : {e}")
    return None

# 그룹 확인
def is_in_blacklist_group(user_id, group_id):
    try:
        response = requests.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
        if response.status_code == 200:
            data = response.json()
            for group in data.get("data", []):
                if group["group"]["id"] == group_id:
                    return True
    except Exception as e:
        print(f"[GH's BotShop] 유저 블랙그룹 찾기 실패 : {e}")
    return False

def is_in_group(user_id, group_id):
    try:
        response = requests.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
        if response.status_code == 200:
            data = response.json()
            for group in data.get("data", []):
                if group["group"]["id"] == group_id:
                    return True  # 그룹에 속함
    except Exception as e:
        print(f"[GH's BotShop] 유저 그룹 찾기 실패: {e}")
    return False  # 그룹에 속하지 않음
# 로그 기록
def log_verification(status, username, user_id=None, reason=None):
    with open("verification_logs.txt", "a" ,encoding='utf-8') as log_file:
        log_entry = f"상태: {status} | 로블록스 닉네임: {username} | 아이디: {user_id} | 사유: {reason}\n"
        log_file.write(log_entry)
    print(log_entry)

# Discord Bot 설정
class VerifyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!!!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)
        print(f"\n\n\n\n\n\n\n\n\n█▀▀▀ █░░█ █ █▀▀   █▀▀▄ █▀▀█ ▀▀█▀▀   █▀▀ █░░█ █▀▀█ █▀▀█\n█░▀█ █▀▀█ ░ ▀▀█   █▀▀▄ █░░█ ░░█░░   ▀▀█ █▀▀█ █░░█ █░░█\n▀▀▀▀ ▀░░▀ ░ ▀▀▀   ▀▀▀░ ▀▀▀▀ ░░▀░░   ▀▀▀ ▀░░▀ ▀▀▀▀ █▀▀▀\nRP 종합봇 by GH's Bot Shop")
bot = VerifyBot()

@bot.event
async def on_ready():
    if Config.status_type == 0:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"{Config.status_message}"))
    if Config.status_type == 1:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.streaming, name=f"{Config.status_message}"))
    if Config.status_type == 2:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"{Config.status_message}"))
    if Config.status_type == 3:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{Config.status_message}"))

@bot.event
async def on_member_join(member):
    # 특정 메시지를 DM으로 전송
    join_message = f"{Config.server_name}에 오신것을 환영합니다, {member.mention}님!"
    embed = discord.Embed(title=":wave:ㆍ반가워요!", description=join_message, color=0x00ff00)
    embed.add_field(name=":date:  입국 날짜", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name=":id:  디스코드 ID", value=member.id, inline=False)
    embed.add_field(name=":name_badge:  닉네임", value=member.display_name, inline=False)
    try:
        # DM 전송 시 예외 처리 추가
        await member.send(embed=embed)
    except discord.errors.HTTPException:
        print(f"[GH's BotShop] 유저에게 DM 전송 실패 : {member.display_name}.")
    # 각 채널에 입장 기록을 남기기
    log_channel = bot.get_channel(Config.join_channel_id)
    if log_channel:
        join_embed = discord.Embed(title="🛬ㆍ입국확인표", color=0x00ff00)
        join_embed.add_field(name=":name_badge:  닉네임", value=f"{member.mention} ({member.display_name})", inline=False)
        join_embed.add_field(name=":id:  디스코드 ID", value=member.id, inline=False)
        join_embed.add_field(name=":date:  입국 날짜", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        await log_channel.send(embed=join_embed)

@bot.event
async def on_member_remove(member):
    # 각 채널에 퇴장 기록을 남기기
    log_channel = bot.get_channel(Config.leave_channel_id)
    if log_channel:
        leave_embed = discord.Embed(title="🛫ㆍ출국확인표", color=0xff0000)
        leave_embed.add_field(name=":name_badge: 닉네임", value=f"{member.mention} ({member.display_name})", inline=False)
        leave_embed.add_field(name=":id: 디스코드 ID", value=member.id, inline=False)
        leave_embed.add_field(name=":date: 출국 날짜", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        await log_channel.send(embed=leave_embed)

def get_group_role(user_id, group_id):
    try:
        response = requests.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
        if response.status_code == 200:
            data = response.json()
            for group in data.get("data", []):
                if group["group"]["id"] == group_id:
                    return group["role"]["name"]  # 역할 이름 반환
    except Exception as e:
        print(f"[GH's BotShop] 그룹 역할 찾기 실패 : {e}")
    return None
# 데이터 저장 및 로드 함수
def save_data(data):
    with open("user_data.json", "w", encoding="UTF-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data():
    try:
        with open("user_data.json", "r", encoding="UTF-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# 초기 데이터 로드
user_data = load_data()
# 인증 버튼 클래스
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

        # 프로필 소개 문구 확인
        description = get_profile_description(self.user_id)
        if description == self.verification_message:
            try:

                # 그룹 역할 확인 및 Discord 역할 지급
                group_role_name = get_group_role(self.user_id, GROUP_ID)

                if not group_role_name:
                    embed = discord.Embed(
                        title="인증 실패",
                        description="그룹 역할 정보를 가져올 수 없습니다.",
                        color=discord.Color.red()
                    )
                    await self.interaction.edit_original_response(embed=embed, view=None)
                    log_verification("Failed", self.username, user_id=self.user_id, reason="No group role found")
                    return

                # Discord 역할 매핑
                role_mapping = Config.role_mapping
                nick_mapping = Config.nick_mapping

                discord_role_name = role_mapping.get(group_role_name, None)
                discord_nick_form = nick_mapping.get(group_role_name, None)

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
                        if self.username in user_data:
                            await self.interaction.edit_original_response(embed=embed, view=None)
                            return
                        # 고유번호 생성 및 저장
                        user_id = len(user_data) + 1
                        user_data[self.username] = {"discord": interaction.user.name, "id": user_id,"money": 0, "License":0}
                        save_data(user_data)
                        new_nickname = Config.nick_form  # 보안상 취약, 권장하지 않음 하지만 보안 처리 잘함 해결될거임 ㅇㅇ 
                        await interaction.user.edit(nick=new_nickname)
                        embed = discord.Embed(
                            title="인증 성공",
                            description=f"로블록스 계정 `{self.username}` 인증이 완료되었습니다!\n-# 지급된 역할: `{discord_role_name}` / 발급된 고유번호 : `{user_id}`",
                            color=discord.Color.green()
                        )
                        await self.interaction.edit_original_response(embed=embed, view=None)
                        return
                    else:
                        raise Exception(f"Role `{discord_role_name}` not found in Discord")

                else:
                    embed = discord.Embed(
                        title="인증 실패",
                        description="매핑된 Discord 역할이 없습니다. 관리자에게 문의하세요.",
                        color=discord.Color.red()
                    )
                    await self.interaction.edit_original_response(embed=embed, view=None)
                    log_verification("Failed", self.username, user_id=self.user_id, reason="역할이 맵핑되어있지 않음.")

            except Exception as e:
                # 오류 발생 시
                embed = discord.Embed(
                    title="인증 실패",
                    description=f"인증은 성공했지만 추가 작업 중 오류가 발생했습니다: {str(e)}",
                    color=discord.Color.red()
                )
                await self.interaction.edit_original_response(embed=embed, view=None)
                log_verification("Failed", self.username, user_id=self.user_id, reason=f"{str(e)}")
        else:
            embed = discord.Embed(title="인증 실패", description="프로필 소개 문구가 올바르지 않습니다.", color=discord.Color.red())
            await self.interaction.edit_original_response(embed=embed, view=None)
            log_verification("Failed", self.username, user_id=self.user_id, reason="소개 문구가 올바르지 않음.")

# 인증 요청 커맨드
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="인증", description="로블록스 계정을 인증합니다.")
async def verify(interaction: discord.Interaction, username: str):
    user_data = load_data()
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
        await interaction.response.send_message(embed=embed)  # ephemeral=True
        log_verification("Failed", username, user_id=user_id, reason="그룹에 가입되어 있지 않음.")
        return

    verification_message = generate_verification_message()
    embed = discord.Embed(
        title="인증 요청",
        description=f"로블록스 프로필 소개 문구를 아래와 같이 변경해주세요:\n`{verification_message}`\n\n변경 후 아래 버튼을 눌러 인증을 완료하세요.",
        color=discord.Color.blue(),
    )
    view = VerifyButton(interaction, user_id, username, verification_message)
    await interaction.response.send_message(embed=embed, view=view)
    
    # verify finish
    
    
    
@bot.tree.command(guild= discord.Object(id=GUILD_ID),name="핑", description="봇의 핑을 확인합니다.")
async def 핑(interaction: discord.Interaction):
    embed = discord.Embed(title="🏓ㆍ퐁!!", description=f'{round(bot.latency * 1000)}ms 걸림!!', color=discord.Color.green())
    await interaction.response.send_message(embed=embed)
        
# 데이터 파일 로드 및 저장
def save_data(data):
    with open("user_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data():
    try:
        with open("user_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
# user_data.json 파일 읽기
with open("user_data.json", "r", encoding='UTF8') as f:
    user_data = json.load(f)
# 특수 접속자 리스트
SPECIAL_ACCESS_FILE = "special_access.json"
ALLOWED_PLAYERS_FILE = "allowed_players.json"
ACCESS_LOG_FILE = "access_log.txt"

# 특수 접속 및 허용 리스트 로드 함수
def load_players(file_path):
    try:
        with open(file_path, "r",encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# 특수 접속 및 허용 리스트 저장 함수
def save_players(file_path, player_list):
    with open(file_path, "w",encoding='utf-8') as f:
        json.dump(player_list, f, ensure_ascii=False, indent=4)

# 특수 접속자 리스트 저장 함수
def save_special_access():
    with open(SPECIAL_ACCESS_FILE, "w",encoding='utf-8') as f:
        json.dump(special_access_players, f, ensure_ascii=False, indent=4)

# 특수 접속자 및 일반 허용 리스트 초기화
special_access_players = load_players(SPECIAL_ACCESS_FILE)
allowed_players = load_players(ALLOWED_PLAYERS_FILE)

# 접속 기록 저장 함수
def log_access(username, allowed, mode):
    with open(ACCESS_LOG_FILE, "a",encoding='utf-8') as log_file:
        log_file.write(
            f"유져명: {username}, 허용여부: {allowed}, 모드: {mode}, 서버상태: {server_status}\n"
        )


# 초기 데이터 로드
user_data = load_data()

import json
from flask import Flask, jsonify, request
import threading
latest_call = None
# 데이터 저장 및 로드 함수
def save_data(data):
    with open("user_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_data():
    try:
        with open("user_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
active_calls = []
# 초기 데이터 로드
user_data = load_data()

# Flask 서버 초기화
app = Flask(__name__)

@app.route('/api/users', methods=['GET'])
def get_all_users():
    user_data = load_data()
    return jsonify(user_data)

USER_DATA_FILE = "user_data.json"

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
def update_discord_money(discord_id, money):
    # 디스코드 메시지 전송
    message = f"<@{discord_id}> 님이 게임에 접속했습니다. 현재 보유 금액: {money}원"
    requests.post("https://discord.com/api/webhooks/1344110935345991701/x1KQDAh9R12PLVPKr2KL7LWrEJtnO75NYdAzqUMak0Uqst2CrlYW4BYldYgu6T4J5PTu", json={"content": message})
@app.route("/get_money/<string:roblox_nickname>", methods=["GET"])
def get_money(roblox_nickname):
    username = roblox_nickname
    if not username:
        return jsonify({"error": "No username provided"}), 400

    user_data = load_user_data()
    money = user_data.get(username, {}).get("money", 0)

    # 디스코드 서버에 돈 변경 반영
    discord_id = user_data.get(username, {}).get("id")  # 디스코드 ID
    if discord_id:
        update_discord_money(discord_id, money)

    return jsonify({"money": money}), 200

@app.route('/api/users/<string:roblox_nickname>', methods=['GET'])
def get_user_by_roblox(roblox_nickname):
    user_data = load_data()
    if roblox_nickname in user_data:
        return jsonify(user_data[roblox_nickname])
    else:
        return jsonify({"error": "User not found"}), 404



@app.route('/api/users', methods=['POST'])
def add_user():
    user_data = load_data()
    data = request.json
    discord_user = data.get("discord_user")
    roblox_nickname = data.get("roblox_nickname")

    if not discord_user or not roblox_nickname:
        return jsonify({"error": "Invalid data"}), 400

    # 중복 확인
    for user, userdata in user_data.items():
        if userdata["roblox"] == roblox_nickname:
            return jsonify({"error": "Roblox nickname already registered", "id": userdata["id"]}), 400

    if discord_user in user_data:
        return jsonify({"error": "Discord user already registered", "id": user_data[discord_user]["id"]}), 400

    # 고유번호 생성 및 저장
    user_id = len(user_data) + 1
    user_data[discord_user] = {"roblox": roblox_nickname, "id": user_id, "money":0, "License":0}
    save_data(user_data)

    return jsonify({"message": "User added", "id": user_id}), 201
@app.route("/receive_call", methods=["POST"])
def receive_call():
    global latest_call
    data = request.json
    latest_call = {
        "team": data.get("team"),
        "caller": data.get("caller"),
        "caller_id": data.get("caller_id"),
        "location": data.get("location"),
        "reason": data.get("reason")
    }
    return jsonify({"status": "success"}), 200

@app.route("/get_call", methods=["GET"])
def get_call():
    global latest_call
    if latest_call:
        call_data = latest_call
        latest_call = {}  # 데이터를 보낸 후 즉시 삭제하여 유지되지 않도록 함
        return jsonify(call_data)
    else:
        return jsonify({"status": "no_call"}), 200
# 접속 확인 API 엔드포인트
@app.route("/check_player", methods=["POST"])
def check_player():
    data = request.json
    roblox_username = data.get("username")

    if not roblox_username:
        return jsonify({"error": "Username is required"}), 400

    # 특수 접속 모드일 경우
    if server_status["special_mode"] == True:
        if roblox_username in special_access_players:
            log_access(roblox_username, True, "special_mode")
            return jsonify({"allowed": True})
        else:
            log_access(roblox_username, False, "special_mode")
            return jsonify({"allowed": False})

    # 서버가 닫혀 있을 경우
    elif not server_status["open"] == True:
        if roblox_username in allowed_players:
            log_access(roblox_username, True, "closed_server")
            return jsonify({"allowed": True})
        else:
            log_access(roblox_username, False, "closed_server")
            return jsonify({"allowed": False})

    # 서버가 열려 있을 경우 (기본 상태)
    else:
        log_access(roblox_username, True, "open_server")
        return jsonify({"allowed": True})
# 데이터 파일 로드
try:
    with open("user_data.json", "r", encoding="utf-8") as f:
        user_data = json.load(f)
except FileNotFoundError:
    user_data = {}

try:
    with open("cars_data.json", "r", encoding="utf-8") as f:
        cars_data = json.load(f)
except FileNotFoundError:
    cars_data = {}

# 데이터 저장 함수
def save_car_data():
    with open("cars_data.json", "w", encoding="utf-8") as f:
        json.dump(cars_data, f, indent=4, ensure_ascii=False)

# Flask API: 차량 데이터 추가
@app.route("/add_car", methods=["POST"])
def add_car():
    data = request.json
    roblox_name = data.get("roblox_name")
    car_name = data.get("car_name")

    # 번호판 생성
    while True:
        number_plate = f"{random.randint(100, 999)}{random.choice('가나다라마바사아자차카타파하')}{random.randint(1000, 9000)}"
        if not any(car["number_plate"] == number_plate for cars in cars_data.values() for car in cars):
            break

    # 차량 데이터 저장
    if roblox_name not in cars_data:
        cars_data[roblox_name] = []
    cars_data[roblox_name].append({"number_plate": number_plate, "car_name": car_name})

    save_car_data()  # 데이터 저장
    return jsonify({"status": "success", "number_plate": number_plate}), 200

# Flask API: 차량 회수
@app.route("/remove_car", methods=["POST"])
def remove_car():
    data = request.json
    number_plate = data.get("number_plate")
    roblox_name = None

    # 번호판으로 차량 찾기 및 삭제
    for name, cars in cars_data.items():
        for car in cars:
            if car["number_plate"] == number_plate:
                roblox_name = name
                cars.remove(car)
                break
        if roblox_name:
            break

    if not roblox_name:
        return jsonify({"상태": "error", "사유": "번호판을 찾을 수 없습니다."}), 404

    save_car_data()  # 데이터 저장
    return jsonify({"status": "success", "owner": roblox_name}), 200

# Flask API: 특정 플레이어의 차량 정보 조회
@app.route("/get_cars", methods=["GET"])
def get_cars():
    roblox_name = request.args.get("roblox_name")
    if roblox_name not in cars_data:
        return jsonify({"상태": "error", "사유": "차량이 없습니다."}), 404

    return jsonify({"status": "success", "cars": cars_data[roblox_name]}), 200
USER_DATA_FILE = "user_data.json"

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@app.route('/update_money', methods=['POST'])
def update_money():
    data = request.json
    roblox_name = data.get("username")
    new_money = data.get("money")

    if not roblox_name or new_money is None:
        return jsonify({"error": "Invalid data"}), 400

    try:
        with open("user_data.json", "r", encoding="utf-8") as f:
            user_data = json.load(f)
    except FileNotFoundError:
        user_data = {}

    if roblox_name in user_data:
        user_data[roblox_name]["money"] = new_money

        with open("user_data.json", "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=4, ensure_ascii=False)

        return jsonify({"상태": "success"})
    else:
        return jsonify({"error": "User not found"}), 404 
BAN_DATA_FILE = "ban_data.json"

def load_ban_data():
    try:
        with open(BAN_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

@app.route("/ban_data", methods=["GET"])
def get_ban_data():
    return jsonify(load_ban_data())

def run_flask():
    app.run(host='0.0.0.0', port=Config.server_port)
    
# Flask 서버 실행 (비동기로 실행)
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
print("[GH's BotShop] 서버가 정상적으로 열렸습니다.")

    # 역할 ID 매핑 (추가 가능)
ROLE_MAPPING = Config.call_role_mapping

@bot.tree.command(guild=discord.Object(id=Config.guild_id),name="호출", description="특정 역할을 호출하여 DM 및 로블록스에 알림을 보냅니다.")
@app_commands.describe(
    role="호출할 역할 선택",
    location="사건이 발생한 위치",
    reason="호출 사유"
)
async def call_command(interaction: discord.Interaction, role: str, location: str, reason: str):
    user_data = load_data()
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
#야후 작동한다!!
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
    try:
        requests.post(f"http://127.0.0.1:{Config.server_port}/receive_call", json=roblox_payload)
    except Exception as e:
        embed = discord.Embed(title=f"{Config.blocked_emoji}ㆍ호출 실패", description=f"로블록스 서버로 알림을 전송하지 못했습니다.\n에러 내용 : {e}", color=discord.Color.red())
        await interaction.response.send_message(embed= embed, ephemeral=True)
        return
    embed = discord.Embed(title=f"{Config.success_emoji}ㆍ호출 성공", description=f"{role}에게 호출 알림을 보냈습니다.", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@call_command.autocomplete("role")
async def role_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=r, value=r)
        for r in ROLE_MAPPING.keys()
        if current.lower() in r.lower()
    ]
@bot.tree.command(guild=discord.Object(GUILD_ID),name="유저정보_확인", description="저장된 유저 정보를 확인합니다.")
@app_commands.describe(discord_user="디스코드 유저 선택")
async def check_user_info(interaction: discord.Interaction, discord_user: discord.User):
    user_data = load_data()
    roblox_names = [
        nickname for nickname, data in user_data.items() if data["discord"] == discord_user.name
    ]

    if not roblox_names:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="유저 정보 없음",
                description=f"{discord_user.name}님은 등록된 정보가 없습니다.",
                color=discord.Color.red()
            )
        )
        return

    # Embed 생성
    embed = discord.Embed(
        title=f"{discord_user.name}님의 유저 정보",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=discord_user.avatar.url if discord_user.avatar else None)

    for roblox_name in roblox_names:
        user_info = user_data[roblox_name]
        # money 값 읽기: 기본값 대신 명시적으로 처리
        money = user_info["money"] if "money" in user_info else 0
        embed.add_field(
            name=f"🔹 로블록스 닉네임: {roblox_name}",
            value=(
                f"- 고유번호: `{user_info['id']}`\n"
                f"- 보유 금액: `{money} 원`\n"
                f"- 면허 종류: `{user_info['License']}`"
            ),
            inline=False
        )

    # 응답 보내기
    await interaction.response.send_message(embed=embed)

# 송금 기록 저장 (성공 및 실패 모두 기록)
def log_transaction(sender, recipient, amount, success=True, reason=None):
    with open("send_money.txt", "a", encoding="utf-8") as file:
        if success:
            file.write(f"[{datetime.now()}] 성공: {sender} -> {recipient}: {amount}원\n")
        else:
            file.write(f"[{datetime.now()}] 실패: {sender} -> {recipient}: {amount}원 | 사유: {reason}\n")

# Discord 사용자 이름으로 로블록스 닉네임 검색
def find_roblox_nickname_by_discord_name(user_data, discord_name):
    for roblox_nickname, data in user_data.items():
        if data["discord"] == discord_name:
            return roblox_nickname
    return None

# 송금 명령어
@bot.tree.command(guild=discord.Object(GUILD_ID),name="송금", description="다른 유저에게 돈을 송금합니다.")
@app_commands.describe(
    recipient="돈을 받을 유저를 선택하세요.",
    amount="송금할 금액을 입력하세요."
)
async def send_money(interaction: discord.Interaction, recipient: discord.Member, amount: int):
    sender_discord = interaction.user.name
    recipient_discord = recipient.name

    if amount <= 0:
        log_transaction(sender_discord, recipient_discord, amount, success=False, reason="금액이 0 이하")
        embed=discord.Embed(title="<:block:1319659240360644659>ㆍ송금 실패", description=f"송금할 금액이 0원 이하입니다.\n-# 송금 시도액 : {amount}", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return
    

    # 유저 데이터 로드
    user_data = load_data()

    # 송금자의 로블록스 닉네임 찾기
    sender_roblox = find_roblox_nickname_by_discord_name(user_data, sender_discord)
    recipient_roblox = find_roblox_nickname_by_discord_name(user_data, recipient_discord)

    if sender_roblox is None:
        log_transaction(sender_discord, recipient_discord, amount, success=False, reason="송금자 정보 없음")
        embed=discord.Embed(title=f"{Config.blocked_emoji}ㆍ송금 실패", description=f"당신의 정보가 없습니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    if recipient_roblox is None:
        log_transaction(sender_discord, recipient_discord, amount, success=False, reason="수령자 정보 없음")
        embed=discord.Embed(title=f"{Config.blocked_emoji}ㆍ송금 실패", description=f"받을 사람의 정보가 없습니다.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    sender_data = user_data[sender_roblox]
    recipient_data = user_data[recipient_roblox]

    if sender_data["money"] < amount:
        log_transaction(sender_discord, recipient_discord, amount, success=False, reason="잔액 부족")
        embed=discord.Embed(title=f"{Config.blocked_emoji}ㆍ송금 실패", description=f"송금할 금액이 부족합니다! \n-# 현재 보유 금액 : {sender_data['money']}\n-# 송금 시도액 : {amount}", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    # 금액 업데이트
    sender_data["money"] -= amount
    recipient_data["money"] += amount
    save_data(user_data)

    # 송금 기록
    log_transaction(sender_data["discord"], recipient_data["discord"], amount, success=True)


    # 성공 메시지
    embed = discord.Embed(title =f"{Config.success_emoji}ㆍ송금 성공!", description=f"{recipient.mention}님에게 {amount}원을 성공적으로 송금했습니다!", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)
@bot.tree.command(guild=discord.Object(GUILD_ID),name="차량확인", description="자신의 소유 차량을 확인합니다.")
async def check_cars(interaction: discord.Interaction):
    user = interaction.user
    roblox_name = None

    # user_data에서 로블록스 닉네임 찾기
    for name, data in user_data.items():
        if data["discord"] == str(user):
            roblox_name = name
            break

    if not roblox_name:
        embed = discord.Embed(title="정보확인실패", description="등록된 로블록스 닉네임이 없습니다.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed)

    # 소유 차량 목록 가져오기
    user_cars = cars_data.get(roblox_name, [])
    if not user_cars:
        embed = discord.Embed(title="정보확인실패", description="소유 차량이 없습니다.", color=discord.Color.red())
        return await interaction.response.send_message(embed=embed)

    # 차량 목록 출력
    car_list = "\n".join([f"차 이름: {car['car_name']} / 번호판: {car['number_plate']}" for car in user_cars])
    embed = discord.Embed(title="소유 차량 목록", description=f"{car_list}", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

# 로그 기록 함수 수정
def log_forced_transaction(sender_id, receiver_id, amount, status):
    with open("forced_transactions.txt", "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 수정된 부분
        log = f"[{timestamp}] 전송자: {sender_id}, 수령자: {receiver_id}, 금액: {amount}, 상태: {status}\n"
        f.write(log)

BAN_DATA_FILE = "ban_data.json"
def load_ban_data():
    try:
        with open(BAN_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_ban_data(data):
    with open(BAN_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content.startswith("!차량회수"):
        user_data = load_data()
        # 특정 역할이 있는지 확인 (역할 ID로 확인)
        role_id = Config.car_steal_id  # 회수를 할 수 있는 역할의 ID
        has_role = any(role.id == role_id for role in message.author.roles)

        if not has_role:
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return

        try:
            # 메시지에서 번호판 추출
            _, number_plate = message.content.split(" ")
            roblox_name = None

            # 번호판으로 차량 찾기 및 삭제
            for name, cars in cars_data.items():
                for car in cars:
                    if car["number_plate"] == number_plate:
                        roblox_name = name
                        cars.remove(car)
                        break
                if roblox_name:
                    break

            if not roblox_name:
                embed=discord.Embed(title="작동 실패", description="해당 번호판에 해당하는 차량이 없습니다.", color=discord.Color.red())
                await message.channel.send(embed=embed)
            else:
                save_car_data()  # 데이터 저장
                embed=discord.Embed(title="회수 성공", description=f"차량 {number_plate}이(가) 회수되었습니다.", color=discord.Color.green())
                await message.channel.send(embed=embed)
        except Exception as e:
            embed=discord.Embed(title="작동 실패", description=f"차량 회수 처리중 오류가 발생하였습니다.\n-# 에러 메시지 : `{e}`", color=discord.Color.red())
            await message.channel.send(embed=embed)
            print(f"[GH's BotShop] 에러 발생! : {e}")
    if message.content == "!도움말":
        if not any(role.id == Config.help_id for role in message.author.roles):
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return
        embed = discord.Embed(title="도움말", description=f"어떤 명령어가 있는지 확인하실 수 있습니다!\n-# 해당 명령어를 옵션 없이 입력시 옵션을 알 수 있습니다.", color=discord.Color.blue())
        embed.add_field(name="!상태변경", value="봇의 ~~ 하는중을 변경시킵니다.", inline=False)
        embed.add_field(name="!강제송금", value="한 유저로부터 다른 유저에게 돈을 강제로 송금시킵니다.", inline=False)
        embed.add_field(name="!고유번호 발급/삭제/변경", value="고유번호를 발급/삭제/변경시킵니다.", inline=False)
        embed.add_field(name="!서버온 / !서버오프 / !특수접속", value="서버 상태를 변경시킵니다.", inline=False)
        embed.add_field(name="!특수추가 / !특수확인", value="특수접속 유저 명단을 추가, 명단 내 인원을 확인합니다.", inline=False)
        embed.add_field(name="!면허지급 / !면허회수", value="특정 유저에게 면허를 지급, 회수합니다.", inline=False)
        embed.add_field(name="!차량회수", value="특정 차량을 삭제시킵니다.", inline=False)
        embed.add_field(name="!밴", value="유저를 인게임, 디스코드에서 밴시킵니다.", inline=False)
        embed.add_field(name="!돈 지급/회수", value="유저에게 돈을 지급, 회수시킵니다.", inline=False)
        await message.channel.send(embed=embed)

    if message.content.startswith("!상태변경"):
        if not any(role.id == Config.status_id for role in message.author.roles):
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return
        parts = message.content.split("/", 2)
        if len(parts) < 3:
            embed=discord.Embed(title="작동 실패", description=f"사용방법 : `!상태변경/[메시지]/[하는중, 듣는중, 시청중, 방송중]`", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return
        
        sta_message, sta_type = parts[1], parts[2]
        status_types = {
            "하는중": discord.Game(name=sta_message),
            "듣는중": discord.Activity(type=discord.ActivityType.listening, name=sta_message),
            "시청중": discord.Activity(type=discord.ActivityType.watching, name=sta_message),
            "방송중": discord.Streaming(name=sta_message, url=f"https://www.twitch.tv/example")
        }
    
        if sta_type not in status_types:
            embed=discord.Embed(title="작동 실패", description="잘못된 유형입니다. (하는중, 듣는중, 시청중, 방송중 중 하나 선택)")
            await message.channel.send(embed=embed)
            return
        await bot.change_presence(activity=status_types[sta_type])
        embed=discord.Embed(title="작동 성공", description=f"상태가 `{sta_message}` `{sta_type}` 으로 변경되었습니다.", color=discord.Color.green())
        await message.channel.send(embed=embed)

    if message.content.startswith("!강제송금"):
        users_data = load_data()
        # 관리자 역할 확인 (역할 ID를 사용)
        if not any(role.id == Config.enforcement_manager_id for role in message.author.roles):  # 관리자 역할 ID 대체
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return

        # 명령어 파싱
        args = message.content.split()
        if len(args) != 4:
            embed=discord.Embed(title="작동 실패", description=f"사용방법 : `!강제송금 [보내는 유저의 고유번호] [받는 유저의 고유번호] [금액]`", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return

        sender_id = args[1]
        receiver_id = args[2]
        try:
            amount = int(args[3])
            if amount <= 0:
                embed=discord.Embed(title="작동 실패", description="송금 금액은 0보다 커야 합니다.", color=discord.Color.red())
                await message.channel.send(embed=embed)
                return
        except ValueError:
            embed=discord.Embed(title="작동 실패", description="송금 금액은 숫자로 입력해야 합니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return

        # 유저 데이터 확인
        sender_data = None
        receiver_data = None

        for username, data in users_data.items():
            if str(data["id"]) == sender_id:
                sender_data = data
            if str(data["id"]) == receiver_id:
                receiver_data = data

        if not sender_data:
            embed=discord.Embed(title="작동 실패", description=f"보내는 유저 ID {sender_id}를 찾을 수 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            log_forced_transaction(sender_id, receiver_id, amount, "실패: 전송자 탐색 실패")
            return

        if not receiver_data:
            embed=discord.Embed(title="작동 실패", description=f"받는 유저 ID {receiver_id}를 찾을 수 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            log_forced_transaction(sender_id, receiver_id, amount, "실패: 수령자 탐색 실패")
            return

        # 송금 처리
        if sender_data["money"] >= amount:
            sender_data["money"] -= amount
            receiver_data["money"] += amount
            save_data(users_data)
            log_forced_transaction(sender_id, receiver_id, amount, "성공")
            embed=discord.Embed(title="송금 완료", description=f"{sender_id}에서 {receiver_id}님께로 {amount}원이 강제로 송금되었습니다.", color=discord.Color.green())
            await message.channel.send(embed=embed)
        else:
            embed=discord.Embed(title="작동 실패", description=f"송금 실패: {sender_id}의 잔액이 부족합니다. 현재 잔액: {sender_data['money']}원", color=discord.Color.red())
            await message.channel.send(embed=embed)
            log_forced_transaction(sender_id, receiver_id, amount, "실패: 잔액부족")

    if message.content.startswith("!고유번호 발급"):
        if not any(role.id == Config.ID_manage_id for role in message.author.roles):
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return
        parts = message.content.split()
        if len(parts) != 4:
            embed=discord.Embed(title="작동 실패", description=f"사용방법 : `!고유번호 발급 [디스코드 유저명] [로블록스 닉네임]`", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return
        user_data = load_data()

        discord_user = parts[2]
        roblox_nickname = parts[3]

    # 이미 같은 로블록스 닉네임이 등록된 경우
        if roblox_nickname in user_data:
            embed=discord.Embed(title="작동 실패", description=f"{roblox_nickname}는 이미 등록되었습니다!\n-# 고유번호: {user_data[roblox_nickname]['id']})", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return

    # 고유번호 생성 및 저장
        user_id = len(user_data) + 1
        user_data[roblox_nickname] = {"discord": discord_user, "id": user_id,"money": 0, "License":"미보유"}
        save_data(user_data)
        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member_named(discord_user)

        new_nickname = f'{user_id}ㆍ직업ㆍ{roblox_nickname}'
        await member.edit(nick=new_nickname)
        embed=discord.Embed(title="발급 성공", description=f"{discord_user}님께 고유번호 {user_id}가 부여되었습니다!\n-# 별명의 직업 부분을 수동으로 변경해주셔야합니다.", color=discord.Color.green())
        await message.channel.send(embed=embed)
    if message.content.startswith("!고유번호 삭제"):
        if not any(role.id == Config.ID_manage_id for role in message.author.roles):
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return
        parts = message.content.split()
        if len(parts) != 3:
            embed=discord.Embed(title="작동 실패", description=f"사용방법 : `!고유번호 삭제 [디스코드 유저명]`", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return
        user_data = load_data()
        discord_user = parts[2]

        if discord_user in user_data:
            del user_data[discord_user]
            save_data(user_data)
            embed=discord.Embed(title="삭제 성공", description=f"{discord_user}님의 고유번호가 삭제되었습니다.", color=discord.Color.green())
            await message.channel.send(embed=embed)
        else:
            embed=discord.Embed(title="작동 실패", description=f"{discord_user}님은 고유번호를 발급받으시지 않았습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
    
    for keyword in fuckList:
        if keyword in message.content:
            guild = bot.get_guild(GUILD_ID)
            member = guild.get_member(message.author.id)
            embed = discord.Embed(title=f"{Config.blocked_emoji}ㆍ검열됨!", description=f"{message.author}님께서 욕설을 사용하셨습니다!\n타임아웃 1분이 지급되었습니다.", color = discord.Color.red())
            await message.channel.send(embed=embed)
            await message.delete()
            await member.timeout(datetime.timedelta(minutes=1), reason=f"욕설 사용 (메시지 : {message})")
            break
    if message.content == "!서버온":
        role = discord.utils.get(message.author.roles, id = Config.server_manager_id)
        if role in message.author.roles: # Check if the author has the role
                embed = discord.Embed(title=f"{Config.server_on}ㆍ서버 활성화", description=f"{Config.serveron_message}", color=discord.Color.blue())
                embed.set_image(url="attachment://output.png")
                button = discord.ui.Button(label="⏩ 들어가기", url=f"https://www.roblox.com/ko/games/{Config.place_id}")
                view = discord.ui.View()
                view.add_item(button)
                server_status["open"] = True
                await message.channel.send(embed=embed, view=view)
                await message.delete()
        else:
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
    if message.content == "!서버오프":
        role = discord.utils.get(message.author.roles, id = Config.server_manager_id)
        if role in message.author.roles: # Check if the author has the role
            embed = discord.Embed(title=f"{Config.server_off}ㆍ서버 비활성화", description=f"{Config.serveroff_message}", color=discord.Color.red())
            embed.set_image(url="attachment://output.png")
            server_status["open"] = False
            await message.channel.send(embed=embed)
            await message.delete()
        else:
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
    if message.content == "!특수접속":
        role = discord.utils.get(message.author.roles, id = Config.server_manager_id)
        if role in message.author.roles: # Check if the author has the role
            embed = discord.Embed(title=f"{Config.special_access}ㆍ특수접속", description=f"{Config.special_message}", color=discord.Color.yellow())
            embed.set_image(url="attachment://output.png")
            button = discord.ui.Button(label="⏩ 들어가기", url=f"https://www.roblox.com/ko/games/{Config.place_id}")
            view = discord.ui.View()
            view.add_item(button)
            server_status["special_mode"] = True
            await message.channel.send(embed=embed, view=view)
            await message.delete()
        else:
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
    if message.content.startswith("!특수추가"):
        # 명령어를 실행한 사용자가 특정 역할을 가졌는지 확인
        member = message.author
        if any(role.id == Config.server_manager_id for role in member.roles):
            # '특수추가' 명령어 뒤에 사용자명을 받아옴
            roblox_username = message.content.split(" ")[1] if len(message.content.split(" ")) > 1 else None

            if roblox_username:
                if roblox_username not in special_access_players:
                    special_access_players.append(roblox_username)
                    save_special_access()  # 변경 사항 저장
                    embed=discord.Embed(title="추가 성공", description=f"{roblox_username}님이 특수 접속 리스트에 추가되었습니다!", color=discord.Color.green())
                    await message.channel.send(embed=embed)
                else:
                    embed=discord.Embed(title="작동 실패", description=f"{roblox_username}님은 이미 특수 접속 리스트에 있습니다.", color=discord.Color.red())
                    await message.channel.send(embed=embed)
            else:
                embed=discord.Embed(title="작동 실패", description="사용자명을 입력해주세요. 예: `!특수추가 [로블록스 닉네임]`", color=discord.Color.red())
                await message.channel.send(embed=embed)
        else:
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            # 역할이 없는 경우, 권한 부족 메시지
            await message.channel.send(embed=embed)
    if message.content == "!특수확인":
        if special_access_players:
            player_list = "\n".join(special_access_players)
            embed=discord.Embed(title="특수 접속 허용자 목록", description=f"{player_list}", color=discord.Color.blue())        
            await message.channel.send(embed=embed)
        else:
            embed=discord.Embed(title="작동 실패", description="현재 특수 접속 허용자 리스트가 비어 있습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
    if message.content.startswith("!면허지급"):
        # 역할 확인
        if not any(role.id == Config.license_manager_id for role in message.author.roles):
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return

        # 명령어 파싱
        parts = message.content.split()
        if len(parts) != 4:
            embed=discord.Embed(title="작동 실패", description=f"사용방법 : `!면허지급 [로블록스 닉네임] [면허 종류(1종, 2종)] [구분(1종 : 대형, 특수, 보통, 소형 / 2종 : 보통, 소형, 원동기장치자전거)]`", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return
        roblox_nickname = parts[1]
        kind_license = parts[2]
        kind22_license = parts[3]


        # 유저 데이터 로드
        user_data = load_data()

        if roblox_nickname not in user_data:
            embed=discord.Embed(title="작동 실패", description=f"로블록스 닉네임 `{roblox_nickname}` 을(를) 찾을 수 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return

        if user_data[roblox_nickname]["License"] != "미보유":
            embed=discord.Embed(title="작동 실패", description=f"`{roblox_nickname}` 님은 이미 면허를 보유하고 있습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return

        # 면허 지급
        user_data[roblox_nickname]["License"] = f"{kind_license}{kind22_license}"
        save_data(user_data)

        # Discord 사용자 검색
        discord_username = user_data[roblox_nickname]["discord"]  # 사용자명
        member = discord.utils.get(message.guild.members, name=discord_username)

        if member:
            try:
                embed = discord.Embed(title="면허 지급됨", description=f"축하드립니다, {roblox_nickname}님께 `{kind_license} {kind22_license}`면허가 지급되었습니다!", color=discord.Color.green())
                await member.send(embed=embed)
                embed=discord.Embed(title="면허 지급 성공", description=f"`{roblox_nickname}` 님에게 `{kind_license} {kind22_license}`면허를 성공적으로 지급했습니다.", color=discord.Color.green())
                await message.channel.send(embed=embed)
            except discord.Forbidden:
                embed=discord.Embed(title="면허 지급 성공", description=f"`{roblox_nickname}` 님에게 `{kind_license} {kind22_license}`면허를 지급했지만 DM을 보낼 수 없습니다.", color=discord.Color.yellow())
                await message.channel.send(embed=embed)
        else:
            embed=discord.Embed(title="작동 실패", description=f"서버에서 `{roblox_nickname}` 님을 찾을 수 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
    if message.content.startswith("!면허회수"):
        # 역할 확인
        if not any(role.id == Config.license_manager_id for role in message.author.roles):
            embed=discord.Embed(title="작동 실패", description="이 명령어를 사용하실 권한이 없습니다.", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return

        # 명령어 파싱
        try:
            _, roblox_nickname = message.content.split()
        except ValueError:
            embed=discord.Embed(title="작동 실패", description=f"사용방법 : `!면허회수 [로블록스 닉네임]`", color=discord.Color.red())
            await message.channel.send(embed=embed)
            return

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

bot.run(TOKEN)



