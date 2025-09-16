import os
from seija.modules.storage_management import BOT_DATA_DIR


if os.environ.get('SEIJA_TOKEN'):
    bot_token = os.environ.get('SEIJA_TOKEN')
else:
    token_file_full_path = os.path.join(BOT_DATA_DIR, "token.txt")
    try:
        with open(token_file_full_path, "r+") as token_file:
            bot_token = token_file.read().strip()
    except FileNotFoundError as e:
        print("i need a bot token. either set SEIJA_TOKEN environment variable")
        print("or put it in:", token_file_full_path)
        raise SystemExit

if os.environ.get('SEIJA_OSU_API_KEY'):
    osu_api_key = os.environ.get('SEIJA_OSU_API_KEY')
else:
    osu_api_key_file_full_path = os.path.join(BOT_DATA_DIR, "osu_api_key.txt")
    try:
        with open(osu_api_key_file_full_path, "r+") as token_file:
            osu_api_key = token_file.read().strip()
    except FileNotFoundError as e:
        print("i need a osu api key. either set SEIJA_OSU_API_KEY environment variable")
        print("or put it in:", osu_api_key_file_full_path)
        raise SystemExit

if os.environ.get('SEIJA_CLIENT_ID'):
    client_id = os.environ.get('SEIJA_CLIENT_ID')
else:
    client_id_file_full_path = os.path.join(BOT_DATA_DIR, "client_id.txt")
    try:
        with open(client_id_file_full_path, "r+") as token_file:
            client_id = token_file.read().strip()
    except FileNotFoundError as e:
        print("i need a osu web client id. either set SEIJA_CLIENT_ID environment variable")
        print("or put it in:", client_id_file_full_path)
        raise SystemExit

if os.environ.get('SEIJA_CLIENT_SECRET'):
    client_secret = os.environ.get('SEIJA_CLIENT_SECRET')
else:
    client_secret_file_full_path = os.path.join(BOT_DATA_DIR, "client_secret.txt")
    try:
        with open(client_secret_file_full_path, "r+") as token_file:
            client_secret = token_file.read().strip()
    except FileNotFoundError as e:
        print("i need a osu web client secret. either set SEIJA_CLIENT_SECRET environment variable")
        print("or put it in:", client_secret_file_full_path)
        raise SystemExit
