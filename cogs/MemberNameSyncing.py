from discord.ext import commands
from modules import db
import time
import asyncio
import datetime
from modules.connections import osu as osu
import osuembed


class MemberNameSyncing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.member_mapping_feed_list = db.query(["SELECT guild_id, channel_id FROM channels "
                                                  "WHERE setting = ?",
                                                  ["member_mapping_feed"]])
        self.notices_channel_list = db.query(["SELECT guild_id, channel_id FROM channels "
                                              "WHERE setting = ?",
                                              ["notices"]])
        if self.member_mapping_feed_list:
            self.bot.loop.create_task(self.member_name_syncing_loop())
        self.bot.loop.create_task(self.event_history_cleanup_loop())

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if before.name != after.name:
            if self.notices_channel_list:
                query = db.query(["SELECT * FROM users WHERE user_id = ?", [str(after.id)]])
                if query:
                    osu_profile = await osu.get_user(u=query[0][1])
                    if osu_profile:
                        for this_guild in self.notices_channel_list:
                            guild = self.bot.get_guild(int(this_guild[0]))

                            notices_channel = self.bot.get_channel(int(this_guild[1]))

                            if notices_channel:
                                member = guild.get_member(int(after.id))
                                await self.sync_nickname(notices_channel, query[0], member, osu_profile)

    async def event_history_cleanup_loop(self):
        print("Event History Cleanup Loop launched!")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(10)
                print(time.strftime("%X %x %Z") + " | event_history_cleanup_loop start")
                before = int(time.time()) - 172800
                db.query(["DELETE FROM user_event_history WHERE timestamp < ?", [before]])
                print(time.strftime("%X %x %Z") + " | event_history_cleanup_loop finished")
                await asyncio.sleep(86400)
            except Exception as e:
                print(time.strftime("%X %x %Z"))
                print("in event_history_cleanup_loop")
                print(e)
                await asyncio.sleep(86400)

    async def member_name_syncing_loop(self):
        print("Member Name Syncing Loop launched!")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(10)
            print(time.strftime("%X %x %Z") + " | member_name_syncing_loop start")
            user_list = db.query("SELECT * FROM users")
            restricted_user_list = db.query("SELECT guild_id, osu_id FROM restricted_users")
            for mapping_feed_channel_id in self.member_mapping_feed_list:

                feed_channel = self.bot.get_channel(int(mapping_feed_channel_id[1]))
                guild = self.bot.get_guild(int(mapping_feed_channel_id[0]))

                guild_notices_channel = db.query(["SELECT channel_id FROM channels "
                                                  "WHERE setting = ? AND guild_id = ?",
                                                  ["notices", str(guild.id)]])

                notices_channel = self.bot.get_channel(int(guild_notices_channel[0][0]))

                for member in guild.members:
                    if member.bot:
                        continue
                    for db_user in user_list:
                        if str(member.id) == str(db_user[0]):
                            try:
                                osu_profile = await osu.get_user(u=db_user[1], event_days="1")
                            except Exception as e:
                                print(e)
                                await asyncio.sleep(120)
                                break
                            if osu_profile:
                                await self.sync_nickname(notices_channel, db_user, member, osu_profile)
                                await self.check_events(feed_channel, osu_profile)
                                if (str(guild.id), str(db_user[1])) in restricted_user_list:
                                    await notices_channel.send(
                                        f"{member.mention} | `{db_user[2]}` | `{db_user[1]}` | "
                                        f"<https://osu.ppy.sh/users/{db_user[1]}> | unrestricted lol")
                                    db.query(["DELETE FROM restricted_users "
                                              "WHERE guild_id = ? AND osu_id = ?",
                                              [str(guild.id), str(db_user[1])]])
                            else:
                                # at this point we are sure that the user is restricted.
                                if not (str(guild.id), str(db_user[1])) in restricted_user_list:
                                    await notices_channel.send(
                                        f"{member.mention} | `{db_user[2]}` | `{db_user[1]}` | "
                                        f"<https://osu.ppy.sh/users/{db_user[1]}> | restricted")
                                    db.query(["INSERT INTO restricted_users VALUES (?,?)",
                                              [str(guild.id), str(db_user[1])]])
                            await asyncio.sleep(1)
            print(time.strftime("%X %x %Z") + " | member_name_syncing_loop finished")
            await asyncio.sleep(7200)

    async def sync_nickname(self, notices_channel, db_user, member, osu_profile):
        now = datetime.datetime.now()
        if "04-01T" in str(now.isoformat()):
            return None
        if str(db_user[2]) != osu_profile.name:
            await notices_channel.send(f"`{db_user[2]}` namechanged to `{osu_profile.name}`. osu_id = `{db_user[1]}`")
            if str(db_user[1]) == str(4116573):
                await notices_channel.send("btw, this is bor. yes, i actually added this specific message for bor.")

        if member.display_name != osu_profile.name:
            if not ("1" in str(db_user[7])):
                old_nickname = member.display_name
                try:
                    await member.edit(nick=osu_profile.name)
                    await notices_channel.send(f"{member.mention} | `{osu_profile.name}` | `{db_user[1]}` | "
                                               f"nickname updated, old nickname `{old_nickname}`")
                except:
                    await notices_channel.send(f"{member.mention} | `{osu_profile.name}` | `{db_user[1]}` | "
                                               f"no perms to update")
        db.query(["UPDATE users SET country = ?, pp = ?, "
                  "osu_join_date = ?, osu_username = ? WHERE user_id = ?;",
                  [str(osu_profile.country), str(osu_profile.pp_raw),
                   str(osu_profile.join_date), str(osu_profile.name), str(member.id)]])

    async def check_events(self, channel, user):
        for event in user.events:
            if not db.query(["SELECT event_id FROM user_event_history WHERE event_id = ?", [str(event.id)]]):
                db.query(["INSERT INTO user_event_history VALUES (?, ?, ?, ?)",
                          [str(user.id), str(event.id), str(channel.id), str(int(time.time()))]])
                event_color = await self.get_event_color(event.display_text)
                if event_color:
                    result = await osu.get_beatmapset(s=event.beatmapset_id)
                    embed = await osuembed.beatmapset(result, event_color)
                    if embed:
                        display_text = event.display_text.replace("@", "")
                        await channel.send(display_text, embed=embed)

    async def get_event_color(self, string):
        if "has submitted" in string:
            return 0x2a52b2
        elif "has updated" in string:
            # return 0xb2532a
            return None
        elif "qualified" in string:
            return 0x2ecc71
        elif "has been revived" in string:
            return 0xff93c9
        elif "has been deleted" in string:
            return 0xf2d7d5
        else:
            return None


def setup(bot):
    bot.add_cog(MemberNameSyncing(bot))
