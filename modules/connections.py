from aioosuapi import aioosuapi
from aioosuwebapi import aioosuwebapi

osu_api_key = (open("data/osu_api_key.txt", "r+").read()).rstrip()
bot_token = (open("data/token.txt", "r+").read()).rstrip()
database_file = 'data/maindb.sqlite3'
osu = aioosuapi.aioosuapi(osu_api_key)
osuweb = aioosuwebapi.aioosuwebapi()
