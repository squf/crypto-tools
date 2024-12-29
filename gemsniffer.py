import asyncio
import websockets
import json
import discord
from discord.ext import tasks
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
DISCORD_TOKEN = os.getenv("gemsniffer_token")
CHANNEL_ID = int(os.getenv("channel_id"))
WEBSOCKET_URL = "wss://pumpportal.fun/api/data"
TRACKED_TOKENS_FILE = "tracked_tokens.json"

# gem parameters, tweak to your liking
TARGET_MARKET_CAP = 20000
TARGET_VOLUME = 10000
TARGET_HOLDERS = 25

posted_tokens = set()

# loads/saves tracked token data to a local .json file for persistence 
def load_tracked_tokens():
    if os.path.exists(TRACKED_TOKENS_FILE):
        with open(TRACKED_TOKENS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_tracked_tokens():
    with open(TRACKED_TOKENS_FILE, "w") as f:
        json.dump(tracked_tokens, f, indent=4, default=str)

tracked_tokens = load_tracked_tokens()

# i'm posting these to a discord but you could tweak this whole thing to work on telegram if you prefer, i just don't have a tg group currently
intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def websocket_listener():
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        await websocket.send(json.dumps({"method": "subscribeNewToken", "params": []}))
        print("Subscribed to new token events.")

        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)

                await process_new_token(data)
            except Exception as e:
                print(f"Error receiving or processing WebSocket data: {e}")

async def process_new_token(data):
    """
    Process new token data and add to tracking list.
    """
    try:
        token_name = data.get("name", "Unknown")
        market_cap = data.get("market_cap", 0)
        volume = data.get("volume", 0)
        holders = data.get("holders", 0)

        if token_name not in tracked_tokens:
            tracked_tokens[token_name] = {
                "timestamp": datetime.utcnow().isoformat(),
                "market_cap": market_cap,
                "volume": volume,
                "holders": holders,
            }
            save_tracked_tokens() 
            print(f"Tracking new token: {token_name}")
    except Exception as e:
        print(f"Error processing token data: {e}")

@tasks.loop(minutes=5)
async def check_tracked_tokens():
    """
    Periodically check tracked tokens for updated metrics.
    """
    for token_name, token_data in list(tracked_tokens.items()):
        market_cap = token_data["market_cap"]
        volume = token_data["volume"]
        holders = token_data["holders"]

        if market_cap >= TARGET_MARKET_CAP and volume >= TARGET_VOLUME and holders >= TARGET_HOLDERS:
            if token_name not in posted_tokens:
                posted_tokens.add(token_name)
                message = (
                    f"**{token_name}** - Market Cap: ${market_cap:,}, Volume: ${volume:,}, Holders: {holders}"
                )
                channel = client.get_channel(CHANNEL_ID)
                await channel.send(message)
                print(f"Posted token: {token_name}")

@client.event
async def on_ready():
    print(f"starting gem sniff as {client.user}")
    asyncio.create_task(websocket_listener())
    check_tracked_tokens.start()

@client.event
async def on_disconnect():
    print("gemsniffer OFFLINE.")

client.run(DISCORD_TOKEN)
