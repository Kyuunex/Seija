import sqlite3
from modules.connections import database_file as database_file
import os


async def add_admins(self):
    async with await self.db.execute("SELECT user_id, permissions FROM admins") as cursor:
        admin_list = await cursor.fetchall()

    if not admin_list:
        app_info = await self.application_info()
        if app_info.team:
            for team_member in app_info.team.members:
                await self.db.execute("INSERT INTO admins VALUES (?, ?)", [int(team_member.id), 1])
                print(f"Added {team_member.name} to admin list")
        else:
            await self.db.execute("INSERT INTO admins VALUES (?, ?)", [int(app_info.owner.id), 1])
            print(f"Added {app_info.owner.name} to admin list")
        await self.db.commit()


def create_tables():
    if not os.path.exists(database_file):
        conn = sqlite3.connect(database_file)
        c = conn.cursor()
        c.execute("""CREATE TABLE "config" ("setting" TEXT, "parent" TEXT, "value" TEXT, "flag" TEXT)""")
        c.execute("""CREATE TABLE "admins" ("user_id" INTEGER, "permissions" INTEGER)""")
        c.execute("""CREATE TABLE "ignored_users" ("user_id" INTEGER, "reason" TEXT)""")

        c.execute("""CREATE TABLE "users" ("user_id" INTEGER, "osu_id" INTEGER, "osu_username" TEXT, 
        "osu_join_date" INTEGER, "pp" INTEGER, "country" TEXT, 
        "ranked_maps_amount" INTEGER, "kudosu" INTEGER, "no_sync" INTEGER)""")

        c.execute("""CREATE TABLE "channels" ("setting" TEXT, "guild_id" INTEGER, "channel_id" INTEGER)""")
        c.execute("""CREATE TABLE "categories" ("setting" TEXT, "guild_id" INTEGER, "category_id" INTEGER)""")
        c.execute("""CREATE TABLE "roles" ("setting" TEXT, "guild_id" INTEGER, "role_id" INTEGER)""")

        c.execute("""CREATE TABLE "mod_post_history" ("post_id" INTEGER, "mapset_id" INTEGER, "channel_id" INTEGER)""")

        c.execute("""CREATE TABLE "mapset_nomination_history" ("event_id" INTEGER, "mapset_id" INTEGER, 
        "channel_id" INTEGER)""")

        c.execute("""CREATE TABLE "mod_tracking" ("mapset_id" INTEGER, "channel_id" INTEGER, "mode" INTEGER)""")

        c.execute("""CREATE TABLE "mapset_notification_status" ("mapset_id" INTEGER, "map_id" INTEGER, 
        "channel_id" INTEGER, "status" INTEGER)""")

        c.execute("""CREATE TABLE "difficulty_claims" ("map_id" INTEGER, "user_id" INTEGER)""")
        c.execute("""CREATE TABLE "restricted_users" ("guild_id" INTEGER, "osu_id" INTEGER)""")

        c.execute("""CREATE TABLE "queues" ( "channel_id" INTEGER, "user_id" INTEGER, 
        "guild_id" INTEGER, "is_creator" INTEGER)""")

        c.execute("""CREATE TABLE "mapset_channels" ("channel_id" INTEGER, "role_id" INTEGER, 
        "user_id" INTEGER, "mapset_id" INTEGER, "guild_id" INTEGER)""")

        c.execute("""CREATE TABLE "member_goodbye_messages" ("message" TEXT)""")

        c.execute("INSERT INTO member_goodbye_messages VALUES (?)", ["%s is going for loved"])
        c.execute("INSERT INTO member_goodbye_messages VALUES (?)", ["%s was told to remap one too many times"])

        conn.commit()
        conn.close()
