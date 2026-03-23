import discord
import os
import datetime
import io
import wave
from discord.ext import commands, voice_recv
from dotenv import load_dotenv
from faster_whisper import WhisperModel

load_dotenv()

# Configuration STT (Modèle 'tiny' pour la rapidité en Codespaces)
model = WhisperModel("tiny", device="cpu", compute_type="int8")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ID du salon à rejoindre automatiquement
VOICE_CHANNEL_ID = 1476970679319658536

def log_text(channel_name, user_name, text):
    day = datetime.datetime.now().strftime("%Y-%m-%d")
    path = f"logs/{day}"
    os.makedirs(path, exist_ok=True)
    
    filename = f"{path}/{channel_name}.txt"
    time_str = datetime.datetime.now().strftime("%H:%M:%S")
    
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{time_str}] {user_name}: {text}\n")

class SpeechToTextSink(voice_recv.AudioSink):
    def __init__(self, channel_name):
        self.channel_name = channel_name
        self.buffers = {}

    def want_opus(self):
        return False

    def write(self, user, data):
        if user not in self.buffers:
            self.buffers[user] = io.BytesIO()
        
        self.buffers[user].write(data.pcm)
        
        # Si le buffer dépasse une certaine taille (ex: 3 secondes d'audio)
        if self.buffers[user].tell() > 48000 * 2 * 3: 
            self.process_audio(user)

    def process_audio(self, user):
        self.buffers[user].seek(0)
        audio_data = self.buffers[user].read()
        self.buffers[user] = io.BytesIO() # Reset buffer

        # Conversion rapide en format que Whisper comprend
        with io.BytesIO() as wav_file:
            with wave.open(wav_file, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(audio_data)
            
            wav_file.seek(0)
            segments, _ = model.transcribe(wav_file, beam_size=5)
            full_text = "".join(segment.text for segment in segments).strip()
            
            if full_text:
                log_text(self.channel_name, user.name, full_text)

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if channel:
        vc = await channel.connect(cls=voice_recv.VoiceRecvClient)
        vc.listen(SpeechToTextSink(channel.name))
        print(f"Écoute automatique sur : {channel.name}")

bot.run(os.getenv("DISCORD_TOKEN"))