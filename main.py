import discord
from discord.ext import commands, tasks
from deep_translator import GoogleTranslator
from gtts import gTTS
import os
import asyncio
import time
import json

# 봇 토큰 (환경 변수 사용)
TOKEN = os.environ["DISCORD_TOKEN"]
SETTINGS_FILE = "settings.json"

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
translator = Translator()

language_map = {
    "중국어": "zh-cn",
    "영어": "en",
    "일본어": "ja"
}

target_language = "zh-cn"
tts_channel_id = None
last_used_time = None
is_tts_playing = False

# ----------------- 설정 저장/불러오기 -----------------
def save_settings():
    data = {
        "target_language": target_language,
        "tts_channel_id": tts_channel_id
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f)

def load_settings():
    global target_language, tts_channel_id
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            target_language = data.get("target_language", "zh-cn")
            tts_channel_id = data.get("tts_channel_id", None)

# ----------------- 봇 이벤트 -----------------
@bot.event
async def on_ready():
    load_settings()
    print(f"{bot.user} 준비 완료!")
    auto_disconnect.start()

# ----------------- 자동 퇴장 -----------------
@tasks.loop(minutes=1)
async def auto_disconnect():
    global last_used_time
    if last_used_time is None:
        return
    
    if time.time() - last_used_time > 600:  # 10분
        for guild in bot.guilds:
            if guild.voice_client:
                await guild.voice_client.disconnect()
        last_used_time = None
        print("10분 미사용 → 자동 퇴장")

# ----------------- 명령어 -----------------
@bot.command()
async def 언어(ctx, lang_name):
    """번역 언어 설정"""
    global target_language
    
    if lang_name in language_map:
        target_language = language_map[lang_name]
        save_settings()
        await ctx.send(f"{lang_name}로 번역하도록 설정되었습니다.")
    else:
        await ctx.send("지원 언어: 중국어 / 영어 / 일본어")

@bot.command()
async def 채널지정(ctx):
    """TTS 채널 지정"""
    global tts_channel_id
    tts_channel_id = ctx.channel.id
    save_settings()
    await ctx.send("이 채널에서만 TTS가 작동합니다.")

@bot.command()
async def 퇴장(ctx):
    """음성 채널에서 나가기"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("음성채널에서 나갔습니다.")

@bot.command()
async def 명령어(ctx):
    """사용 가능한 명령어 안내"""
    commands_list = """
현재 사용 가능한 명령어:
1️⃣ !언어 중국어/영어/일본어 → TTS 번역 언어 설정
2️⃣ !채널지정 → 이 채널에서만 TTS 작동
3️⃣ !퇴장 → 봇 음성 채널에서 나가기
"""
    await ctx.send(commands_list)

# ----------------- 음성 채널 입장 -----------------
async def join_voice_channel(message):
    if message.author.voice:
        channel = message.author.voice.channel
        if not message.guild.voice_client:
            await channel.connect()

# ----------------- 메시지 이벤트 -----------------
@bot.event
async def on_message(message):
    global last_used_time, is_tts_playing

    if message.author.bot:
        return

    await bot.process_commands(message)

    if message.content.startswith("!"):
        return

    if not message.guild:
        return

    if tts_channel_id != message.channel.id:
        return

    await join_voice_channel(message)

    if not message.guild.voice_client:
        return

    vc = message.guild.voice_client

    if is_tts_playing:
        await message.reply("아직 기존 TTS가 끝나지 않았어요.")
        return

    detected = translator.detect(message.content)

    try:
        translated = GoogleTranslator(source='auto', target=target_language).translate(message.content)
        tts_lang = target_language
    except:
        translated = GoogleTranslator(source='auto', target='ko').translate(message.content)
        tts_lang = 'ko'

    text = translated

    tts = gTTS(text=text, lang=tts_lang)
    tts.save("voice.mp3")

    is_tts_playing = True

    def after_playing(error):
        global is_tts_playing
        is_tts_playing = False
        if os.path.exists("voice.mp3"):
            os.remove("voice.mp3")

    vc.play(discord.FFmpegPCMAudio("voice.mp3"), after=after_playing)

    last_used_time = time.time()

bot.run(TOKEN)