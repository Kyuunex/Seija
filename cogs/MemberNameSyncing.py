import discord
from discord.ext import commands
from modules import db
import time
import asyncio
import upsidedown
import datetime
from modules.connections import osu as osu
from osuembed import osuembed

class MemberNameSyncing(commands.Cog, name="Member Name Syncing"):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.member_name_syncing_loop())

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        which_guild = db.query(["SELECT * FROM config WHERE setting = ?", ["guild_user_event_tracker"]])
        if which_guild:
            query = db.query(["SELECT * FROM users WHERE user_id = ?", [str(after.id)]])
            if query:
                osuprofile = await osu.get_user(u=query[0][1])
                if osuprofile:
                    for this_guild in which_guild:
                        guild = self.bot.get_guild(int(this_guild[1]))
                        now = datetime.datetime.now()
                        auditchannel = self.bot.get_channel(int(this_guild[3]))
                        if auditchannel:
                            member = guild.get_member(int(after.id))
                            await self.one_guild_member_sync(auditchannel, query, now, member, osuprofile)

    async def member_name_syncing_loop(self):
        print("Member Name Syncing Loop launched!")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(10)
                print(time.strftime('%X %x %Z')+' | user event tracker')
                memberfeedchannellist = db.query(["SELECT * FROM config WHERE setting = ?", ["guild_user_event_tracker"]])
                if memberfeedchannellist:
                    now = datetime.datetime.now()
                    for onechannel in memberfeedchannellist:
                        auditchannel = self.bot.get_channel(int(onechannel[3]))
                        feedchannel = self.bot.get_channel(int(onechannel[2]))
                        guild = self.bot.get_guild(int(onechannel[1]))
                        for member in guild.members:
                            if not member.bot:
                                query = db.query(["SELECT * FROM users WHERE user_id = ?", [str(member.id)]])
                                if query:
                                    #print(time.strftime('%X %x %Z')+" | mapping_username_loop currently checking %s" % (str(query[0][1])))
                                    try:
                                        check_if_restricted_user_in_db = db.query(["SELECT osu_id FROM restricted_users WHERE guild_id = ? AND osu_id = ?", [str(guild.id), str(query[0][1])]])
                                        osuprofile = await osu.get_user(u=query[0][1], event_days="1")
                                        if osuprofile:
                                            await self.one_guild_member_sync(auditchannel, query, now, member, osuprofile)
                                            await self.check_events(feedchannel, osuprofile, "user_event_history", str(feedchannel.id))
                                            if check_if_restricted_user_in_db:
                                                await auditchannel.send("%s | `%s` | `%s` | <https://osu.ppy.sh/users/%s> | unrestricted lol" % (member.mention, str(query[0][2]), str(query[0][1]), str(query[0][1])))
                                                db.query(["DELETE FROM restricted_users WHERE guild_id = ? AND osu_id = ?", [str(guild.id), str(query[0][1])]])
                                        else:
                                            # at this point we are sure that the user is restricted.
                                            if not check_if_restricted_user_in_db:
                                                await auditchannel.send("%s | `%s` | `%s` | <https://osu.ppy.sh/users/%s> | restricted" % (member.mention, str(query[0][2]), str(query[0][1]), str(query[0][1])))
                                                db.query(["INSERT INTO restricted_users VALUES (?,?)", [str(guild.id), str(query[0][1])]])
                                    except Exception as e:
                                        print(e)
                                        print("Connection issues?")
                                        await asyncio.sleep(120)
                                else:
                                    await self.send_notice("%s | not in db" % (member.mention), auditchannel, now)
                                await asyncio.sleep(1)
                print(time.strftime('%X %x %Z')+' | mapping username loop finished')
                await asyncio.sleep(3600)
            except Exception as e:
                print(time.strftime('%X %x %Z'))
                print("in member_name_syncing_loop")
                print(e)
                await asyncio.sleep(7200)

    async def one_guild_member_sync(self, auditchannel, query, now, member, osuprofile):
        if "04-01T" in str(now.isoformat()):
            osuusername = upsidedown.transform(osuprofile.name)
        else:
            osuusername = osuprofile.name
        if str(query[0][2]) != osuusername:
            await auditchannel.send("`%s` namechanged to `%s`. osu_id = `%s`" % (str(query[0][2]), osuusername, str(query[0][1])))
            if str(query[0][1]) == str(4116573):
                await auditchannel.send("This is bor btw. Yes, I actually added this specific message for bor in this bot.")
        if member.display_name != osuusername:
            if "1" in str(query[0][7]):
                await self.send_notice("%s | `%s` | `%s` | username not updated as `no_sync` was set for this user" % (str(member.mention), osuusername, str(query[0][1])), auditchannel, now)
            else:
                old_nickname = member.display_name
                try:
                    await member.edit(nick=osuusername)
                except Exception as e:
                    await auditchannel.send(e)
                    await auditchannel.send("%s | `%s` | `%s` | no perms to update" % (member.mention, osuusername, str(query[0][1])))
                await auditchannel.send("%s | `%s` | `%s` | nickname updated, old nickname `%s`" % (member.mention, osuusername, str(query[0][1]), old_nickname))
        db.query(
            [
                "UPDATE users SET country = ?, pp = ?, osu_join_date = ?, osu_username = ? WHERE user_id = ?;",
                [
                    str(osuprofile.country),
                    str(osuprofile.pp_raw),
                    str(osuprofile.join_date),
                    str(osuprofile.name),
                    str(member.id)
                ]
            ]
        )

    async def send_notice(self, notice, channel, now):
        if not db.query(["SELECT notice FROM notices WHERE notice = ?", [notice]]):
            await channel.send(notice)
            db.query(["INSERT INTO notices VALUES (?, ?)", [str(now.isoformat()), notice]])

    async def check_events(self, channel, user, history_table_name, channel_id = 0):
        print(time.strftime('%X %x %Z')+" | currently checking %s" % (user.name))
        for event in user.events:
            if not db.query(["SELECT event_id FROM %s WHERE event_id = ?" % (history_table_name), [str(event.id)]]):
                db.query(["INSERT INTO %s VALUES (?, ?, ?)" % (history_table_name), [str(user.id), str(event.id), str(channel_id)]])
                event_color = await self.get_event_color(event.display_text)
                if event_color:
                    result = await osu.get_beatmapset(s=event.beatmapset_id)
                    embed = await osuembed.beatmapset(result, event_color)
                    if embed:
                        display_text = (event.display_text).replace("@", "")
                        print(display_text)
                        await channel.send(display_text, embed=embed)

    async def get_event_color(self, string):
        if 'has submitted' in string:
            return 0x2a52b2
        elif 'has updated' in string:
            #return 0xb2532a
            return None
        elif 'qualified' in string:
            return 0x2ecc71
        elif 'has been revived' in string:
            return 0xff93c9
        elif 'has been deleted' in string:
            return 0xf2d7d5
        else:
            return None

def setup(bot):
    bot.add_cog(MemberNameSyncing(bot))
