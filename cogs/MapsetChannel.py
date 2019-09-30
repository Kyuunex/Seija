from modules import db
from cogs.Docs import mapchannelmanagement
from modules import permissions
from osuembed import osuembed
import discord
from discord.ext import commands
import random
import asyncio

from modules.connections import osu as osu


class MapsetChannel(commands.Cog, name="Mapset Management Commands"):
    def __init__(self, bot):
        self.bot = bot
        self.mapset_owner_default_permissions = discord.PermissionOverwrite(
            create_instant_invite=True,
            manage_channels=True,
            manage_roles=True,
            manage_webhooks=True,
            read_messages=True,
            send_messages=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            mention_everyone=False
        )

    @commands.command(name="add", brief="Add a user in the current mapset channel", description="", pass_context=True)
    async def addm(self, ctx, user_id: str):
        await self.mapset_channelsettings(ctx, "add", user_id)

    @commands.command(name="remove", brief="Remove a user from the current mapset channel", description="", pass_context=True)
    async def removem(self, ctx, user_id: str):
        await self.mapset_channelsettings(ctx, "remove", user_id)

    @commands.command(name="abandon", brief="Abandon the mapset and untrack", description="", pass_context=True)
    async def abandon(self, ctx):
        guildarchivecategory = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_archive_category", str(ctx.guild.id)]])
        if guildarchivecategory:
            if (db.query(["SELECT * FROM mapset_channels WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (permissions.check(ctx.message.author.id)):
                if db.query(["SELECT * FROM mapset_channels WHERE channel_id = ?", [str(ctx.message.channel.id)]]):
                    try:
                        mapset_id = db.query(["SELECT mapset_id FROM mod_tracking WHERE channel_id = ?", [str(ctx.message.channel.id)]])
                        if mapset_id:
                            db.query(["DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",[str(mapset_id[0][0]), str(ctx.message.channel.id)]])
                            db.query(["DELETE FROM mod_posts WHERE mapset_id = ? AND channel_id = ?",[str(mapset_id[0][0]), str(ctx.message.channel.id)]])
                            await ctx.send("untracked")
                            await asyncio.sleep(1)

                        archivecategory = self.bot.get_channel(int(guildarchivecategory[0][0]))
                        await ctx.message.channel.edit(reason=None, category=archivecategory)
                        await ctx.send("Abandoned and moved to archive")
                    except Exception as e:
                        await ctx.send(e)
                else:
                    await ctx.send("%s this is not a mapset channel" % (ctx.message.author.mention))
            else:
                await ctx.send("%s this is not your mapset channel" % (ctx.message.author.mention))
        else:
            await ctx.send("no archive category set for this server")

    @commands.command(name="setid", brief="Set a mapset id for this channel", description="Useful if you created this channel without setting an id", pass_context=True)
    async def set_mapset_id(self, ctx, mapset_id: int):
        if (db.query(["SELECT * FROM mapset_channels WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (permissions.check(ctx.message.author.id)):
            try:
                db.query(["UPDATE mapset_channels SET mapset_id = ? WHERE channel_id = ?;", [str(mapset_id), str(ctx.message.channel.id)]])
                await ctx.send("Mapset id updated for this channel")
            except Exception as e:
                await ctx.send(e)

    @commands.command(name="setowner", brief="Transfer set ownership to another discord account", description="user_id can only be that discord account's id", pass_context=True)
    async def set_owner_id(self, ctx, user_id: int):
        if (db.query(["SELECT * FROM mapset_channels WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (permissions.check(ctx.message.author.id)):
            try:
                member = ctx.guild.get_member(int(user_id))
                if member:
                    db.query(["UPDATE mapset_channels SET user_id = ? WHERE channel_id = ?;", [str(user_id), str(ctx.message.channel.id)]])
                    await ctx.message.channel.set_permissions(target=member, overwrite=self.mapset_owner_default_permissions)
                    await ctx.send("Owner updated for this channel")
            except Exception as e:
                await ctx.send(e)

    @commands.command(name="chanlist", brief="List all mapset channel", description="", pass_context=True)
    async def chanlist(self, ctx):
        if permissions.check(ctx.message.author.id):
            for oneentry in db.query("SELECT * FROM mapset_channels"):
                await ctx.send(content="channel_id <#%s> | role_id %s | user_id <@%s> | mapset_id %s | guild_id %s " % (oneentry))
        else:
            await ctx.send(embed=permissions.error())

    @commands.command(name="nuke", brief="Nuke a requested mapset channel", description="", pass_context=True)
    async def nuke(self, ctx):
        if permissions.check(ctx.message.author.id):
            role_idlist = db.query(["SELECT role_id FROM mapset_channels WHERE channel_id = ?", [str(ctx.message.channel.id)]])
            if role_idlist:
                try:
                    await ctx.send("nuking channel and role in 2 seconds! untracking also")
                    await asyncio.sleep(2)
                    role = discord.utils.get(ctx.guild.roles, id=int(role_idlist[0][0]))

                    mapset_id = db.query(["SELECT mapset_id FROM mod_tracking WHERE channel_id = ?", [str(ctx.message.channel.id)]])
                    if mapset_id:
                        db.query(["DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?", [str(mapset_id[0][0]), str(ctx.message.channel.id)]])
                        db.query(["DELETE FROM mod_posts WHERE mapset_id = ? AND channel_id = ?", [str(mapset_id[0][0]), str(ctx.message.channel.id)]])
                        await ctx.send("untracked")
                        await asyncio.sleep(2)

                    db.query(["DELETE FROM mapset_channels WHERE channel_id = ?", [str(ctx.message.channel.id)]])
                    await role.delete(reason="Manually nuked the role due to abuse")
                    await ctx.message.channel.delete(reason="Manually nuked the channel due to abuse")
                except Exception as e:
                    await ctx.send(e)
            else:
                await ctx.send("this is not a mapset channel")
        else:
            await ctx.send(embed=permissions.error())

    @commands.command(name="request_mapset_channel", brief="Request ether a queue or mod channel", description="", pass_context=True)
    async def make_mapset_channel(self, ctx, mapset_id = None, mapset_title = None):
        guildmapsetcategory = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_mapset_category", str(ctx.guild.id)]])
        if guildmapsetcategory:
            try:
                await ctx.send("sure, gimme a moment")
                if int(mapset_id) == 0 or mapset_id == None:
                    mapset = None
                    mapset_id = "0"
                    desc = ""
                else:
                    try:
                        mapset = await osu.get_beatmapset(s=mapset_id)
                    except:
                        mapset = None
                        print("Connection issues?")
                    mapset_id = str(mapset_id)
                    desc = "https://osu.ppy.sh/beatmapsets/%s" % (mapset_id)

                if mapset_title:
                    discordfriendlychannelname = mapset_title.replace(" ", "_").lower()
                    rolename = mapset_title
                elif mapset:
                    discordfriendlychannelname = mapset.title.replace(" ", "_").lower()
                    rolename = mapset.title
                else:
                    discordfriendlychannelname = None
                    rolename = None

                if discordfriendlychannelname:
                    guild = ctx.message.guild
                    rolecolor = discord.Colour(random.randint(1, 16777215))
                    mapsetrole = await guild.create_role(name=rolename, colour=rolecolor, mentionable=True)
                    category = self.bot.get_channel(int(guildmapsetcategory[0][0]))
                    channeloverwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        ctx.message.author: self.mapset_owner_default_permissions,
                        mapsetrole: discord.PermissionOverwrite(read_messages=True),
                        guild.me: discord.PermissionOverwrite(
                            manage_channels=True,
                            read_messages=True,
                            send_messages=True,
                            embed_links=True
                        )
                    }
                    channel = await guild.create_text_channel(discordfriendlychannelname, overwrites=channeloverwrites, category=category, topic=desc)
                    await ctx.message.author.add_roles(mapsetrole)
                    await channel.send("%s done!" % (ctx.message.author.mention), embed=await mapchannelmanagement())
                    db.query(["INSERT INTO mapset_channels VALUES (?, ?, ?, ?, ?)", [str(channel.id), str(mapsetrole.id), str(ctx.message.author.id), str(mapset_id), str(ctx.guild.id)]])
                else:
                    await ctx.send("You are not using this command correctly")
            except Exception as e:
                print(e)
                await ctx.send("This did not work. You probably specified something incorrectly. Look at the instructions carefully.")
        else:
            await ctx.send("Not enabled in this server yet.")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, deleted_channel):
        try:
            db.query(["DELETE FROM mapset_channels WHERE channel_id = ?",[str(deleted_channel.id)]])
            db.query(["DELETE FROM mod_tracking WHERE channel_id = ?",[str(deleted_channel.id)]])
            db.query(["DELETE FROM mod_posts WHERE channel_id = ?",[str(deleted_channel.id)]])
            print("channel %s is deleted" % (deleted_channel.name))
        except Exception as e:
            print(e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        mapsets_user_is_in = db.query(["SELECT channel_id, role_id FROM mapset_channels WHERE user_id = ?", [str(member.id)]])
        if mapsets_user_is_in:
            for mapset in mapsets_user_is_in:
                channel = self.bot.get_channel(int(mapset[0]))
                if channel:
                    role = discord.utils.get(channel.guild.roles, id=int(mapset[1]))
                    await member.add_roles(role, reason="set owner returned")
                    await channel.set_permissions(target=member, overwrite=self.mapset_owner_default_permissions)
                    await channel.send("the mapset owner has returned. next time you track the mapset, it will be unarchived, unless this is already ranked. ether way, permissions restored.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        mapsets_user_is_in = db.query(["SELECT channel_id FROM mapset_channels WHERE user_id = ?", [str(member.id)]])
        if mapsets_user_is_in:
            for mapset in mapsets_user_is_in:
                channel = self.bot.get_channel(int(mapset[0]))
                if channel:
                    await channel.send("the mapset owner has left the server")
                    db.query(["DELETE FROM mod_tracking WHERE channel_id = ?",[str(channel.id)]])
                    db.query(["DELETE FROM mod_posts WHERE channel_id = ?",[str(channel.id)]])
                    await channel.send("untracked everything in this channel")
                    guildarchivecategory = db.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_archive_category", str(channel.guild.id)]])
                    if guildarchivecategory:
                        archivecategory = self.bot.get_channel(int(guildarchivecategory[0][0]))
                        await channel.edit(reason=None, category=archivecategory)
                        await channel.send("channel archived!")

    async def mapset_channelsettings(self, ctx, action, user_id):
        role_idlist = db.query(["SELECT role_id FROM mapset_channels WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])
        if role_idlist:
            try:
                member = ctx.guild.get_member_named(user_id)
                if not member:
                    try:
                        member = ctx.guild.get_member(int(user_id))
                    except Exception as e:
                        print(e)
                        member = None
                if member:
                    role = discord.utils.get(ctx.guild.roles, id=int(role_idlist[0][0]))
                    if action == "add":
                        await member.add_roles(role, reason="added to mapset")
                        await ctx.send("added %s in this channel" % (member.mention))
                    elif action == "remove":
                        await member.remove_roles(role, reason="removed from mapset")
                        await ctx.send("removed %s from this channel" % (member.mention))
                else:
                    await ctx.send("No member found with what you specified. If you are specifying a name, names are case sensetive.")
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.send("not your mapset channel")


def setup(bot):
    bot.add_cog(MapsetChannel(bot))
