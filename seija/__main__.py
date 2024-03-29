#!/usr/bin/env python3

from discord.ext import commands
import aiosqlite
from aioosuapi import aioosuapi
from aioosuwebapi import aioosuwebapi
from aioosuwebapi.scraper import aioosuwebscraper
import discord
import os


from seija.modules import first_run
from seija.modules import permissions
from seija.manifest import VERSION
from seija.manifest import CONTRIBUTORS

from seija.modules.storage_management import database_file
from seija.modules.connections import bot_token
from seija.modules.connections import osu_api_key
from seija.modules.connections import client_id
from seija.modules.connections import client_secret


if os.environ.get('SEIJA_PREFIX'):
    command_prefix = os.environ.get('SEIJA_PREFIX')
else:
    command_prefix = "."


initial_extensions = [
    "seija.cogs.BotManagement",
    "seija.cogs.Docs",
    "seija.cogs.MapsetChannel",
    "seija.cogs.MemberManagement",
    "seija.cogs.MemberInfoSyncing",
    "seija.cogs.MemberStatistics",
    "seija.cogs.MemberVerification",
    "seija.cogs.MemberVerificationWithMapset",
    "seija.cogs.ModChecker",
    "seija.cogs.Osu",
    "seija.cogs.Queue",
    "seija.cogs.QueueMaintenance",
]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class Seija(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.background_tasks = []

        self.app_version = VERSION
        self.project_contributors = CONTRIBUTORS

        self.description = f"Seija {self.app_version}"
        self.database_file = database_file
        self.db = None
        self.osu = None
        self.osuweb = None
        self.osuscraper = None

    async def setup_hook(self):
        self.db = await aiosqlite.connect(self.database_file)

        await first_run.ensure_tables(self.db)
        await first_run.add_admins(self)
        await permissions.load_users(self.db)

        self.osu = aioosuapi(osu_api_key)
        self.osuweb = aioosuwebapi(client_id, client_secret)
        self.osuscraper = aioosuwebscraper()

        async with self.db.execute("SELECT extension_name FROM user_extensions") as cursor:
            user_extensions = await cursor.fetchall()

        for extension in initial_extensions:
            await self.load_extension(extension)

        for user_extension in user_extensions:
            try:
                await self.load_extension(user_extension[0])
                print(f"User extension {user_extension[0]} loaded")
            except discord.ext.commands.errors.ExtensionNotFound as ex:
                print(ex)

    async def close(self):
        # Cancel all Task object generated by cogs.
        # This prevents any task still running due to having long sleep time.
        for task in self.background_tasks:
            task.cancel()

        # Close osu web api session
        if self.osuweb:
            await self.osuweb.close()

        # Close connection to the database
        if self.db:
            await self.db.close()

        # Run actual discord.py close.
        # await super().close()

        # for now let's just quit() since the thing above does not work :c
        quit()

    async def on_ready(self):
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("------")


client = Seija(command_prefix=command_prefix, intents=intents)
client.run(bot_token)
