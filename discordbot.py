"""this bot will report crypto token prices in a channel based on coinbase information

ex: !check xrp = will post the current price of xrp in channel, along with some animated .gifs in a card format

will require some set-up on your end, including an .env file with a coinbase API key and your discord API key
"""

import os
import discord
from discord.ext import commands
from discord import Embed, File
import ccxt
import random

api_key = os.getenv("discordbot_coinbase_key")
api_secret = os.getenv("discordbot_coinbase_secret", "")
api_secret = api_secret.replace("\\n", "\n")

try:
    coinbase = ccxt.coinbase({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
except Exception as e:
    print(f"Error initializing Coinbase exchange: {e}")
    coinbase = None

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def get_all_trade_pairs():
    if coinbase:
        try:
            markets = coinbase.fetch_markets()
            return {m['symbol'].split('/')[0].lower(): m['symbol'] for m in markets if '/USD' in m['symbol']}
        except Exception as e:
            print(f"discordbot sez: error fetching trade pairs: {e}")
    return {}

dynamic_trade_pairs = get_all_trade_pairs()

def get_trade_pair(symbol):
    return dynamic_trade_pairs.get(symbol.lower())

@bot.event
async def on_ready():
    print(f"discordbot sez: hi i'm {bot.user} and i just fucking love fetching crypto data all the time!")

def fetch_price(trade_pair):
    if not coinbase:
        print("Coinbase exchange is not initialized.")
        return None
    try:
        ticker = coinbase.fetch_ticker(trade_pair)
        price = ticker['last']  
        return price
    except Exception as e:
        print(f"discordbot sez: error fetching price for {trade_pair}: {e}")
        return None

@bot.command(name='check', help='check a crypto price from coinbase - usage: !check [symbol]')
async def check_price(ctx, symbol: str):
    trade_pair = get_trade_pair(symbol)

    if not trade_pair:
        await ctx.send(f"discordbot sez: invalid symbol '{symbol}'.")
        return

    price = fetch_price(trade_pair)

    if price is not None:
        gif_choices = [
            "/home/discordbot/discordbot/discordbot.gif",
            "/home/discordbot/discordbot/discordbot1.gif",
            "/home/discordbot/discordbot/discordbot2.gif",
            "/home/discordbot/discordbot/discordbot3.gif",
            "/home/discordbot/discordbot/discordbot4.gif",
            "/home/discordbot/discordbot/discordbot5.gif",
            "/home/discordbot/discordbot/discordbot6.gif",
        ]
        selected_gif = random.choice(gif_choices)

        embed = Embed(title="crypto check", color=0x1abc9c)
        embed.add_field(name=f"{trade_pair}", value=f"${price:,.2f}", inline=False)
        embed.set_image(url=f"attachment://{os.path.basename(selected_gif)}")
        embed.set_footer(text="powered by discordbot")

        await ctx.send(embed=embed, file=File(selected_gif))
    else:
        await ctx.send(f"discordbot sez: could not retrieve the price for '{symbol}'.")

TOKEN = os.getenv("discord_bot_token")
bot.run(TOKEN)
