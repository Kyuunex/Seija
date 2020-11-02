import sqlite3
from modules.connections import database_file as database_file


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


def ensure_tables():
    conn = sqlite3.connect(database_file)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS "config" (
        "setting"    TEXT, 
        "parent"    TEXT,
        "value"    TEXT,
        "flag"    TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS "admins" (
        "user_id"    INTEGER NOT NULL UNIQUE,
        "permissions"    INTEGER NOT NULL
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS "ignored_users" (
        "user_id"    INTEGER NOT NULL UNIQUE,
        "reason"    TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "users" (
        "user_id"    INTEGER NOT NULL UNIQUE,
        "osu_id"    INTEGER NOT NULL,
        "osu_username"    TEXT NOT NULL,
        "osu_join_date"    INTEGER,
        "pp"    INTEGER,
        "country"    TEXT,
        "ranked_maps_amount"    INTEGER,
        "kudosu"    INTEGER,
        "no_sync"    INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "channels" (
        "setting"    TEXT NOT NULL,
        "guild_id"    INTEGER NOT NULL,
        "channel_id"    INTEGER NOT NULL
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS "categories" (
        "setting"    TEXT NOT NULL,
        "guild_id"    INTEGER NOT NULL,
        "category_id"    INTEGER NOT NULL
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS "roles" (
        "setting"    TEXT NOT NULL,
        "guild_id"    INTEGER NOT NULL,
        "role_id"    INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "mod_post_history" (
        "post_id"    INTEGER NOT NULL,
        "mapset_id"    INTEGER NOT NULL,
        "channel_id"    INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "mapset_nomination_history" (
        "event_id"    INTEGER NOT NULL,
        "mapset_id"    INTEGER NOT NULL,
        "channel_id"    INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "mod_tracking" (
        "mapset_id"    INTEGER NOT NULL,
        "channel_id"    INTEGER NOT NULL,
        "mode"    INTEGER NOT NULL,
        "frequency"    INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "mapset_notification_status" (
        "mapset_id"    INTEGER NOT NULL,
        "map_id"    INTEGER,
        "channel_id"    INTEGER NOT NULL,
        "status"    INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "difficulty_claims" (
        "map_id"    INTEGER NOT NULL,
        "user_id"    INTEGER NOT NULL
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS "restricted_users" (
        "guild_id"    INTEGER NOT NULL,
        "osu_id"    INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "queues" (
        "channel_id"    INTEGER NOT NULL,
        "user_id"    INTEGER NOT NULL,
        "guild_id"    INTEGER NOT NULL,
        "is_creator"    INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "mapset_channels" (
        "channel_id"    INTEGER NOT NULL UNIQUE,
        "role_id"    INTEGER NOT NULL UNIQUE,
        "user_id"    INTEGER NOT NULL,
        "mapset_id"    INTEGER,
        "guild_id"    INTEGER NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "member_goodbye_messages" (
        "message"    TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS "post_verification_messages" (
        "guild_id"    INTEGER NOT NULL,
        "message"    TEXT NOT NULL
    )
    """)

    c.execute("INSERT INTO member_goodbye_messages VALUES (?)", ["%s is going for loved"])
    c.execute("INSERT INTO member_goodbye_messages VALUES (?)", ["%s was told to remap one too many times"])

    conn.commit()
    conn.close()
