import logging
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import gspread
from google.oauth2 import service_account
from gspread_formatting import *

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)

bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())
client = discord.Client(intents=discord.Intents.all())
# Role ID that will control the bot. Left click on role name and copy ID to get it (must have developer options enabled on Discord)
required_role_id = 943552706319114333
# Category ID where new channels will be created
category_id = 975448514198929408
# Category ID where channels will be archived
file_category_id = 975470536169758812
tasks = {}

scope = ['https://www.googleapis.com/auth/spreadsheets']
# Enable Google Spreadsheets API and get your .json credentials file
credentials = service_account.Credentials.from_service_account_file('your/path/to/googlecredentials.json', scopes=scope)
gc = gspread.authorize(credentials)
# Paste below your Google Spreadsheet ID (it's the unique string in the URL for that specific spreadsheet)
spreadsheet_id = 'YOUR-SPREADSHEET-ID'

current_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

@bot.command(name='new_task')
async def create_task(ctx, name: str, url: str, description: str, reward: float, time: float):
    if required_role_id not in [role.id for role in ctx.author.roles]:
        await ctx.send("Oops! ✋ Forbidden 🛑 ")
        return

    category = bot.get_channel(category_id)

    channel = await category.create_text_channel(name=name)

    role = await ctx.guild.create_role(name=name)
    await channel.set_permissions(role, send_messages=True, read_messages=True)

    expiration_time = datetime.utcnow() + timedelta(hours=time)

    tasks[name] = (channel.id, expiration_time, role.name, {'URL': url, 'Description': description, 'Reward': reward})

    embed = discord.Embed(title=f'Hi! There is a new task for {name}! 😎 Come and participate!', color=0xffa500)
    embed.add_field(name='URL', value=url, inline=False)
    embed.add_field(name='Description', value=description, inline=False)
    embed.add_field(name='Reward', value=f'{reward}$', inline=False)
    message = await channel.send(embed=embed)

    await message.pin()

    await message.channel.send("@everyone")

    await countdown(channel, expiration_time)

async def countdown(channel, expiration_time):
    while True:
        time_remaining = expiration_time - datetime.utcnow()

        if time_remaining.total_seconds() <= 0:
            break

        formatted_time = str(time_remaining).split('.')[0]
        await channel.send(f'⏳ Remaining time: {formatted_time}')

        if time_remaining.total_seconds() % 300 == 0:
            await channel.send("Complete to earn rewards!")

        await asyncio.sleep(1800)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    channel_id = message.channel.id
    for task in tasks.values():
        if channel_id == task[0]:
            expiration_time = task[1]
            if datetime.utcnow() > expiration_time:
                await message.channel.send("This task expired. Users cannot send any more messages.")
                return

            if message.attachments:
                role = discord.utils.get(message.guild.roles, name=task[2])
                await message.author.add_roles(role)
                embed = discord.Embed(
                    title=f'@{message.author.name} uploaded a capture! 📸',
                    description=f"Role {role.name} granted! 🛂",
                    color=0x00ff00
                )
                await message.channel.send(embed=embed)
                return

    await bot.process_commands(message)

@bot.command(name='close_task')
async def close_task(ctx, name: str):
    if required_role_id not in [role.id for role in ctx.author.roles]:
        await ctx.send("Oops! ✋ Forbidden 🛑")
        return

    if name not in tasks:
        await ctx.send(f"Oops! ✋ The task '{name}' does not exist")
        return

    channel_id, _, role_name, task_data = tasks[name]

    channel = bot.get_channel(channel_id)
    role = discord.utils.get(ctx.guild.roles, name=role_name)

    participants = [member for member in ctx.guild.members if role in member.roles]

    worksheet = gc.open_by_key(spreadsheet_id).sheet1

    if len(worksheet.get("A1:F1")) == 0:
        headers = ["Task name", "URL", "Description", "Reward", "Username", "Date"]
        worksheet.append_row(headers)
        
        header_range = worksheet.range('A1:F1')

        format_cell_range(worksheet, header_range, CellFormat(backgroundColor=(1, 0.8, 0.4)))

    payment_value = task_data["Reward"]
    total_payment = len(participants) * float(payment_value)

    for participant in participants:
        row_data = [name, task_data["URL"], task_data["Description"], payment_value, participant.name, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')]
        worksheet.append_row(row_data)

    payment_column = worksheet.find("Reward").col
    worksheet.update_cell(len(worksheet.col_values(payment_column)), payment_column, total_payment)

    del tasks[name]

    await ctx.send(f'The {name} task was closed successfully ✅')

    await channel.delete()
    await role.delete()


# Create a bot at Discord devs platform [https://discord.com/developers/applications] and get the token for that bot
bot.run("YOUR_DISCORD_BOT_TOKEN")