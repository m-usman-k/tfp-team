import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

prefix = ["tpf!", "TPF!"]

client = commands.Bot(command_prefix=prefix, case_insensitive=True, intents=intents)

@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="Food orders"))
    print("Logged in!")
    await client.tree.sync()

@client.command()
async def sync(ctx) -> None:
    try:
        fmt = await ctx.bot.tree.sync()
        await ctx.send(f"Synced {len(fmt)} commands.")
    except Exception as e:
        print(e)

async def load():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            try:
                print(f"Attempting to load {file[:-3]}")
                await client.load_extension(f"cogs.{file[:-3]}")
            except Exception as e:
                print(f"Failed to load extension {file[:-3]}")
                print(e)

async def main():
    await load()
    load_dotenv()
    await client.start(os.getenv("BOT_TOKEN"))

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())