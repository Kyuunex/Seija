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


async def ensure_tables(db):
    await db.execute("""
    CREATE TABLE IF NOT EXISTS "config" (
        "setting"    TEXT, 
        "parent"    TEXT,
        "value"    TEXT,
        "flag"    TEXT
    )
    """)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS "admins" (
        "user_id"    INTEGER NOT NULL UNIQUE,
        "permissions"    INTEGER NOT NULL
    )
    """)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS "ignored_users" (
        "user_id"    INTEGER NOT NULL UNIQUE,
        "reason"    TEXT
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "users" (
        "user_id"    INTEGER NOT NULL UNIQUE,
        "osu_id"    INTEGER NOT NULL,
        "osu_username"    TEXT NOT NULL,
        "osu_join_date"    INTEGER,
        "pp"    INTEGER,
        "country"    TEXT,
        "ranked_maps_amount"    INTEGER,
        "kudosu"    INTEGER,
        "no_sync"    INTEGER,
        "confirmed"    INTEGER
    )
    """)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS "user_extensions" (
        "extension_name"     TEXT
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "channels" (
        "setting"    TEXT NOT NULL,
        "guild_id"    INTEGER NOT NULL,
        "channel_id"    INTEGER NOT NULL
    )
    """)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS "categories" (
        "setting"    TEXT NOT NULL,
        "guild_id"    INTEGER NOT NULL,
        "category_id"    INTEGER NOT NULL
    )
    """)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS "roles" (
        "setting"    TEXT NOT NULL,
        "guild_id"    INTEGER NOT NULL,
        "role_id"    INTEGER NOT NULL
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "mod_post_history" (
        "post_id"    INTEGER NOT NULL,
        "mapset_id"    INTEGER NOT NULL,
        "channel_id"    INTEGER NOT NULL
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "mapset_nomination_history" (
        "event_id"    INTEGER NOT NULL,
        "mapset_id"    INTEGER NOT NULL,
        "channel_id"    INTEGER NOT NULL
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "mod_tracking" (
        "mapset_id"    INTEGER NOT NULL,
        "channel_id"    INTEGER NOT NULL,
        "mode"    INTEGER NOT NULL,
        "frequency"    INTEGER NOT NULL
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "mapset_notification_status" (
        "mapset_id"    INTEGER NOT NULL,
        "map_id"    INTEGER,
        "channel_id"    INTEGER NOT NULL,
        "status"    INTEGER NOT NULL
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "difficulty_claims" (
        "map_id"    INTEGER NOT NULL,
        "user_id"    INTEGER NOT NULL
    )
    """)
    await db.execute("""
    CREATE TABLE IF NOT EXISTS "restricted_users" (
        "guild_id"    INTEGER NOT NULL,
        "osu_id"    INTEGER NOT NULL
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "queues" (
        "channel_id"    INTEGER NOT NULL,
        "user_id"    INTEGER NOT NULL,
        "guild_id"    INTEGER NOT NULL,
        "is_creator"    INTEGER NOT NULL
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "mapset_channels" (
        "channel_id"    INTEGER NOT NULL UNIQUE,
        "role_id"    INTEGER NOT NULL UNIQUE,
        "user_id"    INTEGER NOT NULL,
        "mapset_id"    INTEGER,
        "guild_id"    INTEGER NOT NULL
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "member_goodbye_messages" (
        "message"    TEXT NOT NULL UNIQUE
    )
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS "post_verification_messages" (
        "guild_id"    INTEGER NOT NULL,
        "message"    TEXT NOT NULL
    )
    """)

    async with await db.execute("SELECT COUNT(*) FROM member_goodbye_messages ") as cursor:
        amount_of_goodbye_messages = await cursor.fetchone()

    if int(amount_of_goodbye_messages[0]) == 0:
        await db.execute("INSERT OR IGNORE INTO member_goodbye_messages VALUES (?)", ["%s has left"])

    await db.commit()
