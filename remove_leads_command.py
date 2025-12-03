import os
import requests
from dotenv import load_dotenv

os.chdir("/root/scraper_service_bot")
load_dotenv("yad2bot.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
commands = [
    {"command": "start", "description": "Start the bot"}
]

response = requests.post(url, json={"commands": commands})
result = response.json()
print(f"Response: {result}")
if result.get("ok"):
    print("✅ /leads command removed successfully!")
else:
    print("❌ Error:", result.get("description"))
