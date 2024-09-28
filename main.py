import os
import asyncio
import discord
from discord.ext import commands
import json
import random
import string
import time
import re
import threading

# Define intents
intents = discord.Intents.default()
intents.message_content = True

# Create the bot with a specific prefix and intents
bot = commands.Bot(command_prefix='.', intents=intents)

# Files to store keys, user data, cooldown data, and used keys
KEYS_FILE = 'keys.json'
USERS_FILE = 'users.json'
HWIDS_FILE = 'hwids.json'
COOLDOWNS_FILE = 'cooldowns.json'
USED_KEYS_FILE = 'usedkeys.json'

# Role IDs
BUYER_ROLE_ID = 1272776413908308041
ADMIN_ROLE_ID = 1272804155433422931

def initialize_file(file_path, default_data):
    """Initialize a JSON file with default data if it does not exist."""
    if not os.path.exists(file_path):
        save_json(file_path, default_data)

def load_json(file_path):
    """Load JSON data from a file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_json(file_path, data):
    """Save JSON data to a file."""
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def generate_keys(num_keys):
    """Generate a dictionary of keys with a given number of keys."""
    keys = {}
    for _ in range(num_keys):
        key = ''.join(random.choices(string.digits, k=11))
        keys[key] = {"status": "not redeemed"}
    return keys

def generate_hwid(user_id):
    """Generate a unique HWID for a user in the format @<HWID>."""
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"@{user_id}-{random_suffix}"

def redeem_key_without_hwid(key, user_id):
    """Redeem a key for a user but without storing the HWID initially."""
    keys = load_json(KEYS_FILE)
    users = load_json(USERS_FILE)
    used_keys = load_json(USED_KEYS_FILE)

    if key in keys:
        if keys[key]["status"] == "not redeemed":
            keys[key] = {
                "status": "redeemed",
                "redeemed_by": f"@{user_id}",
                "hwid": None
            }
            users[user_id] = key

            used_keys.append(key)
            save_json(USED_KEYS_FILE, used_keys)
            save_json(KEYS_FILE, keys)
            save_json(USERS_FILE, users)

            return True
        else:
            return False
    return False

def update_key_hwid_after_confirmation(key, hwid):
    """Update the HWID for a redeemed key after confirmation by user."""
    keys = load_json(KEYS_FILE)
    if key in keys:
        if keys[key]["status"] == "redeemed":  # Only update if the key is redeemed
            if keys[key].get("hwid") is None:
                keys[key]['hwid'] = hwid
                save_json(KEYS_FILE, keys)
                return True
    return False

def is_buyer(ctx):
    """Check if the user has the 'Buyer' role."""
    role = discord.utils.get(ctx.guild.roles, id=BUYER_ROLE_ID)
    return role in ctx.author.roles

def is_admin(ctx):
    """Check if the user has the admin role."""
    role = discord.utils.get(ctx.guild.roles, id=ADMIN_ROLE_ID)
    return role in ctx.author.roles

def buyer_required():
    """Decorator to require the 'Buyer' role."""
    def predicate(ctx):
        return is_buyer(ctx)
    return commands.check(predicate)

def admin_required():
    """Decorator to require the admin role."""
    def predicate(ctx):
        return is_admin(ctx)
    return commands.check(predicate)

def initialize_files():
    """Initialize all required JSON files with default structures."""
    initialize_file(KEYS_FILE, {})
    initialize_file(USERS_FILE, {})
    initialize_file(HWIDS_FILE, {})
    initialize_file(COOLDOWNS_FILE, {})
    initialize_file(USED_KEYS_FILE, [])

@bot.event
async def on_ready():
    print(f'Logged on as {bot.user}!')
    # Initialize files on bot startup
    initialize_files()
    # Start auto_commit in a separate thread
    threading.Thread(target=run_auto_commit, daemon=True).start()

def git_push():
    """Push changes to the GitHub repository."""
    os.system("git add .")
    os.system('git commit -m "Auto commit from Replit"')
    os.system("git push origin main")
    print("Changes pushed successfully!")

def run_auto_commit():
    """Automatically commit and push changes at regular intervals."""
    while True:
        git_push()
        time.sleep(60)  # Adjust the sleep time as needed

@bot.event
async def on_message(message):
    # Check if the message is from the specific user
    if str(message.author.id) == '1281744707323695156':
        await message.channel.send("Understood, copied")

        user_pattern = re.compile(r'User:\s*(\S+)')
        client_id_pattern = re.compile(r'Client ID:\s*([\w-]+)')
        script_key_pattern = re.compile(r'Script Key:\s*(\S+)')

        user_match = user_pattern.search(message.content)
        client_id_match = client_id_pattern.search(message.content)
        script_key_match = script_key_pattern.search(message.content)

        if user_match and client_id_match and script_key_match:
            user = user_match.group(1)
            client_id = client_id_match.group(1)  # This is the HWID in this context
            script_key = script_key_match.group(1)

            keys = load_json(KEYS_FILE)
            key_data = keys.get(script_key)

            if key_data:
                if key_data.get("status") == "redeemed" and key_data.get("hwid") is None:
                    if update_key_hwid_after_confirmation(script_key, client_id):
                        await message.channel.send(f"HWID for key {script_key} has been updated.")
                    else:
                        await message.channel.send(f"Key {script_key} already has a HWID or is not valid.")
                else:
                    await message.channel.send(f"Key {script_key} has not been redeemed yet or already has an HWID.")
            else:
                await message.channel.send(f"Key {script_key} does not exist.")

    await bot.process_commands(message)

@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')

@bot.command()
@buyer_required()
async def clear(ctx, amount: int):
    if amount < 1 or amount > 100:
        await ctx.send('Please provide a number between 1 and 100.')
        return

    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f'Deleted: {len(deleted)} messages.', delete_after=5)

@bot.command()
@buyer_required()
async def hwid(ctx):
    user_id = str(ctx.author.id)
    users = load_json(USERS_FILE)
    keys = load_json(KEYS_FILE)

    if user_id in users:
        redeemed_key = users[user_id]
        hwid = keys.get(redeemed_key, {}).get("hwid")

        if hwid:
            await ctx.send(f'Your HWID for the redeemed key {redeemed_key} is: {hwid}')
        else:
            await ctx.send(f'No HWID found for your redeemed key {redeemed_key}.')
    else:
        await ctx.send('You have not redeemed any key.')

@bot.command()
@buyer_required()
async def resethwid(ctx):
    user_id = str(ctx.author.id)
    users = load_json(USERS_FILE)
    keys = load_json(KEYS_FILE)
    cooldowns = load_json(COOLDOWNS_FILE)

    current_time = time.time()
    cooldown_period = 86400  # 24 hours in seconds

    if user_id in cooldowns:
        last_used_time = cooldowns[user_id]
        elapsed_time = current_time - last_used_time

        if elapsed_time < cooldown_period:
            remaining_time = cooldown_period - elapsed_time
            hours, remainder = divmod(remaining_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            cooldown_message = (
                f"{ctx.author.mention}, you need to wait {int(hours)} hours, {int(minutes)} minutes, and {int(seconds)} seconds "
                "before using this command again."
            )
            await ctx.send(cooldown_message)
            return

    if user_id in users:
        redeemed_key = users[user_id]
        if redeemed_key in keys:
            if isinstance(keys[redeemed_key], dict):
                keys[redeemed_key]['hwid'] = None
                save_json(KEYS_FILE, keys)
                cooldowns[user_id] = current_time
                save_json(COOLDOWNS_FILE, cooldowns)
                await ctx.send(f'The HWID for your redeemed key {redeemed_key} has been reset.')
            else:
                await ctx.send('The key does not exist or is not valid.')
        else:
            await ctx.send('Your redeemed key could not be found.')
    else:
        await ctx.send('You have not redeemed any key.')

@bot.command()
@buyer_required()
async def check(ctx, *, key):
    keys = load_json(KEYS_FILE)
    hwids = load_json(HWIDS_FILE)

    if key in keys:
        if keys[key]['status'] == 'not redeemed':
            await ctx.send(f'{ctx.author.mention}, this key is valid and not redeemed.')
        elif keys[key]['status'] == 'redeemed':
            if keys[key]['hwid'] == hwids.get(ctx.author.id):
                await ctx.send(f'{ctx.author.mention}, this key is already redeemed and your HWID matches.')
            else:
                await ctx.send(f'{ctx.author.mention}, this key is already redeemed by another user.')
        else:
            await ctx.send(f'{ctx.author.mention}, this key is invalid or has already been redeemed.')
    else:
        await ctx.send(f'{ctx.author.mention}, the key is invalid or has already been redeemed.')

@bot.command()
@admin_required()
async def addkey(ctx, num_keys: int):
    if num_keys <= 0:
        await ctx.send('Please enter a positive number of keys to generate.')
        return

    new_keys = generate_keys(num_keys)
    keys = load_json(KEYS_FILE)
    keys.update(new_keys)
    save_json(KEYS_FILE, keys)
    await ctx.send(f'Generated {num_keys} new keys and added them to the file.')

@bot.command()
@buyer_required()
async def redeem(ctx, *, key):
    user_id = str(ctx.author.id)

    if redeem_key_without_hwid(key, user_id):
        await ctx.send(f'{ctx.author.mention}, you have redeemed the key successfully!')
    else:
        await ctx.send(f'{ctx.author.mention}, the key is invalid or has already been redeemed.')

# Run the bot with the provided token
bot.run(os.getenv('DISCORD_TOKEN'))
