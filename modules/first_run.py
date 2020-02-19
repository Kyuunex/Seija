import sqlite3
from modules.connections import database_file as database_file
import os


async def add_admins(self):
    async with await self.db.execute("SELECT * FROM admins") as cursor:
        admin_list = await cursor.fetchall()

    if not admin_list:
        app_info = await self.application_info()
        if app_info.team:
            for team_member in app_info.team.members:
                await self.db.execute("INSERT INTO admins VALUES (?, ?)", [str(team_member.id), "1"])
                print(f"Added {team_member.name} to admin list")
        else:
            await self.db.execute("INSERT INTO admins VALUES (?, ?)", [str(app_info.owner.id), "1"])
            print(f"Added {app_info.owner.name} to admin list")
        await self.db.commit()


def create_tables():
    if not os.path.exists(database_file):
        conn = sqlite3.connect(database_file)
        c = conn.cursor()
        c.execute("CREATE TABLE config (setting, parent, value, flag)")
        c.execute("CREATE TABLE admins (user_id, permissions)")
        db.query("CREATE TABLE users "
                 "(user_id, osu_id, osu_username, osu_join_date, pp, country, ranked_maps_amount, no_sync)")
        db.query("CREATE TABLE user_event_history (osu_id, event_id, channel_id, timestamp)")
        db.query("CREATE TABLE config (setting, parent, value, flag)")

        db.query("CREATE TABLE channels (setting, guild_id, channel_id)")
        db.query("CREATE TABLE categories (setting, guild_id, category_id)")
        db.query("CREATE TABLE roles (setting, guild_id, role_id)")

        db.query("CREATE TABLE admins (user_id, permissions)")
        db.query("CREATE TABLE mod_posts (post_id, mapset_id, channel_id)")
        db.query("CREATE TABLE mapset_events (event_id, mapset_id, channel_id)")
        db.query("CREATE TABLE mod_tracking (mapset_id, channel_id, mode)")
        db.query("CREATE TABLE mod_tracking_pauselist (mapset_id, channel_id, mode)")
        db.query("CREATE TABLE mapset_notification_status (mapset_id, map_id, channel_id, status)")
        db.query("CREATE TABLE map_owners (map_id, user_id)")
        db.query("CREATE TABLE notices (timestamp, notice)")
        db.query("CREATE TABLE restricted_users (guild_id, osu_id)")
        db.query("CREATE TABLE queues (channel_id, user_id, guild_id)")
        db.query("CREATE TABLE mapset_channels (channel_id, role_id, user_id, mapset_id, guild_id)")
        db.query("CREATE TABLE name_backups (id, name)")
        db.query("CREATE TABLE member_goodbye_messages (message)")
        db.query(["INSERT INTO member_goodbye_messages VALUES (?)", ["%s is going for loved"]])
        db.query(["INSERT INTO member_goodbye_messages VALUES (?)", ["%s was told to remap one too many times"]])
        conn.commit()
        conn.close()
