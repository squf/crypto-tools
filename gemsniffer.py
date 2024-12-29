import asyncio
import websockets
import json
import discord
from discord.ext import tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# setup an .env file in the script directory with a discord api key & discord channel id
load_dotenv()
DISCORD_TOKEN = os.getenv("gemsniffer_token")
CHANNEL_ID = int(os.getenv("channel_id"))
WEBSOCKET_URL = "wss://pumpportal.fun/api/data"
TRACKED_TOKENS_FILE = "tracked_tokens.json"

# adjust gem parameters here
TARGET_MARKET_CAP = 50
TARGET_VOLUME = 25.0

tokens = {}
def save_tracked_tokens():
    with open(TRACKED_TOKENS_FILE, "w") as file:
        json.dump(tokens, file, indent=4)

def load_tracked_tokens():
    if os.path.exists(TRACKED_TOKENS_FILE):
        with open(TRACKED_TOKENS_FILE, "r") as file:
            return json.load(file)
    return {}

@tasks.loop(hours=1)
async def prune_tokens():
    global tokens
    now = datetime.utcnow()
    pruned = []
    for token_name, token_data in list(tokens.items()):
        token_time = datetime.fromisoformat(token_data["timestamp"])
        if (now - token_time).total_seconds() > 86400: 
            if (token_data["market_cap"] < TARGET_MARKET_CAP or
                token_data["volume"] < TARGET_VOLUME):
                pruned.append(token_name)
                del tokens[token_name]
    
    if pruned:
        print(f"Pruned tokens: {', '.join(pruned)}")
        save_tracked_tokens()

def reset_tokens():
    global tokens
    tokens = {}
    save_tracked_tokens()
    print("Reset all tracked tokens.")

tokens = load_tracked_tokens()

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def process_new_token(data):
    global tokens

    try:
        name = data.get("name", "Unknown")
        market_cap = data.get("marketCapSol", 0)
        sol_amount = data.get("solAmount", 0)
        mint_address = data.get("mint", None) 

        if name not in tokens:
            tokens[name] = {
                "timestamp": datetime.utcnow().isoformat(),
                "market_cap": market_cap,
                "volume": sol_amount,
                "mint": mint_address, 
            }
        else:
            tokens[name]["market_cap"] = market_cap
            tokens[name]["volume"] += sol_amount
          
        if (tokens[name]["market_cap"] >= TARGET_MARKET_CAP and
                tokens[name]["volume"] >= TARGET_VOLUME):
            
            link = f"https://pump.fun/coin/{mint_address}"
            shortened_link = f"[{mint_address[:6]}]({link})" if mint_address else "[No Link Available]"

            channel = client.get_channel(CHANNEL_ID)
            await channel.send(
                f"**{name}** gem sniffed! 🚀 {shortened_link}\n"
                f"- Market Cap: {tokens[name]['market_cap']}\n"
                f"- Volume: {tokens[name]['volume']}"
            )
        
        save_tracked_tokens()

    except Exception as e:
        print(f"Error processing token data: {e}")

async def websocket_listener():
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        await websocket.send(json.dumps({"method": "subscribeNewToken", "params": []}))
        print("websocket connected")
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"websocket data: {data}")
                await process_new_token(data)
            except Exception as e:
                print(f"websocket error: {e}")

@tasks.loop(hours=1)
async def periodic_prune():
    await prune_tokens()

@tasks.loop(seconds=1209600)
async def periodic_reset():
    global tokens
    tokens = {}
    save_tracked_tokens()
    print("reset tracked tokens")

@client.event
async def on_ready():
    print(f"sniffing for gems as {client.user}")
    asyncio.create_task(websocket_listener())
    periodic_prune.start()
    periodic_reset.start()

@client.event
async def on_disconnect():
    print("gemsniffer OFFLINE")
  
client.run(DISCORD_TOKEN)
