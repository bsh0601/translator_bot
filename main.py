import discord
from discord.ext import commands
import json
import os
from gtts import gTTS
from deep_translator import GoogleTranslator
from keep_alive import keep_alive

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

SETTINGS_FILE = "settings.json"

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"target_language": "en", "tts_channel_id": None}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@bot.event
async def on_ready():
    print(f"{bot.user} 로그인 완료")

@bot.command()
async def 언어(ctx, lang):
    settings = load_settings()

    language_map = {
        "영어": "en",
        "일본어": "ja",
        "중국어": "zh"
    }

    if lang not in language_map:
        await ctx.send("지원 언어: 영어 / 일본어 / 중국어")
        return

    settings["target_language"] = language_map[lang]
    save_settings(settings)

    await ctx.send(f"{lang} 로 설정 완료!")

@bot.command()
async def 채널지정(ctx):
    settings = load_settings()
    settings["tts_channel_id"] = ctx.channel.id
    save_settings(settings)
    await ctx.send("이 채널을 TTS 채널로 설정 완료!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    settings = load_settings()
    tts_channel_id = settings.get("tts_channel_id")
    target_language = settings.get("target_language")

    if message.channel.id != tts_channel_id:
        return

    if not message.author.voice:
        return

    try:
        translated = GoogleTranslator(
            source="auto",
            target=target_language
        ).translate(message.content)

        print("번역 결과:", translated)

        # 🔥 gTTS는 zh-CN 필요
        if target_language == "zh":
            tts_lang = "zh-CN"
        else:
            tts_lang = target_language

    except Exception as e:
        print("번역 오류:", e)
        translated = message.content
        tts_lang = "ko"

    tts = gTTS(text=translated, lang=tts_lang)
    tts.save("tts.mp3")

    voice_channel = message.author.voice.channel

    if not message.guild.voice_client:
        vc = await voice_channel.connect()
    else:
        vc = message.guild.voice_client

    vc.play(discord.FFmpegPCMAudio("tts.mp3"))

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))