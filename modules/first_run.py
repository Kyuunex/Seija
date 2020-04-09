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
        c.execute("CREATE TABLE users "
                  "(user_id, osu_id, osu_username, osu_join_date, pp, country, ranked_maps_amount, no_sync)")
        c.execute("CREATE TABLE user_event_history (osu_id, event_id, channel_id, timestamp)")

        c.execute("CREATE TABLE channels (setting, guild_id, channel_id)")
        c.execute("CREATE TABLE categories (setting, guild_id, category_id)")
        c.execute("CREATE TABLE roles (setting, guild_id, role_id)")

        c.execute("CREATE TABLE rankfeed_channel_list (channel_id)")
        c.execute("CREATE TABLE rankfeed_history (mapset_id)")

        c.execute("CREATE TABLE usereventfeed_tracklist (osu_id)")
        c.execute("CREATE TABLE usereventfeed_channels (osu_id, channel_id)")
        c.execute("CREATE TABLE usereventfeed_history (osu_id, event_id, timestamp)")

        c.execute("CREATE TABLE groupfeed_channel_list (channel_id)")
        c.execute("CREATE TABLE groupfeed_group_members (osu_id, group_id)")
        c.execute("CREATE TABLE groupfeed_member_info (osu_id, username, country)")

        c.execute("CREATE TABLE mod_posts (post_id, mapset_id, channel_id)")
        c.execute("CREATE TABLE mapset_events (event_id, mapset_id, channel_id)")
        c.execute("CREATE TABLE mod_tracking (mapset_id, channel_id, mode)")
        c.execute("CREATE TABLE mod_tracking_pauselist (mapset_id, channel_id, mode)")
        c.execute("CREATE TABLE mapset_notification_status (mapset_id, map_id, channel_id, status)")
        c.execute("CREATE TABLE map_owners (map_id, user_id)")
        c.execute("CREATE TABLE notices (timestamp, notice)")
        c.execute("CREATE TABLE restricted_users (guild_id, osu_id)")
        c.execute("CREATE TABLE queues (channel_id, user_id, guild_id, is_creator)")
        c.execute("CREATE TABLE mapset_channels (channel_id, role_id, user_id, mapset_id, guild_id)")
        c.execute("CREATE TABLE name_backups (id, name)")
        c.execute("CREATE TABLE member_goodbye_messages (message)")
        c.execute("INSERT INTO member_goodbye_messages VALUES (?)", ["%s is going for loved"])
        c.execute("INSERT INTO member_goodbye_messages VALUES (?)", ["%s was told to remap one too many times"])
        conn.commit()
        conn.close()
