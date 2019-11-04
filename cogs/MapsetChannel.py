from modules import db
from cogs.Docs import Docs
from modules import permissions
import discord
from discord.ext import commands
import random
import asyncio

from modules.connections import osu as osu


class MapsetChannel(commands.Cog, name="Mapset Management Commands"):
    def __init__(self, bot):
        self.bot = bot
        self.docs = Docs(bot)
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
        self.mapset_bot_default_permissions = discord.PermissionOverwrite(
            manage_channels=True,
            manage_roles=True,
            read_messages=True,
            send_messages=True,
            embed_links=True
        )

    @commands.command(name="add", brief="Add a user in the current mapset channel")
    async def add(self, ctx, user_id: str):
        role_id_list = db.query(["SELECT role_id FROM mapset_channels "
                                 "WHERE user_id = ? AND channel_id = ?",
                                 [str(ctx.author.id), str(ctx.channel.id)]])
        if role_id_list:
            try:
                member = await self.get_member_by_name_or_id(ctx, user_id)
                if member:
                    role = discord.utils.get(ctx.guild.roles, id=int(role_id_list[0][0]))
                    await member.add_roles(role, reason="added to mapset")
                    await ctx.send("added %s in this channel" % member.mention)
                else:
                    await ctx.send("No member found with what you specified. "
                                   "If you are specifying a name, names are case sensitive.")
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.send("not your mapset channel")

    @commands.command(name="remove", brief="Remove a user from the current mapset channel")
    async def remove(self, ctx, user_id: str):
        role_id_list = db.query(["SELECT role_id FROM mapset_channels "
                                 "WHERE user_id = ? AND channel_id = ?",
                                 [str(ctx.author.id), str(ctx.channel.id)]])
        if role_id_list:
            try:
                member = await self.get_member_by_name_or_id(ctx, user_id)
                if member:
                    role = discord.utils.get(ctx.guild.roles, id=int(role_id_list[0][0]))
                    await member.remove_roles(role, reason="removed from mapset")
                    await ctx.send("removed %s from this channel" % member.mention)
                else:
                    await ctx.send("No member found with what you specified. "
                                   "If you are specifying a name, names are case sensitive.")
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.send("not your mapset channel")

    async def get_member_by_name_or_id(self, ctx, user_id):
        try:
            if user_id.isdigit():
                return ctx.guild.get_member(int(user_id))
            else:
                return ctx.guild.get_member_named(user_id)
        except Exception as e:
            print(e)
            return None

    @commands.command(name="claim_diff", brief="Claim a difficulty", description="")
    @commands.check(permissions.is_admin)
    async def claim_diff(self, ctx, map_id):
        db.query(["INSERT INTO map_owners VALUES (?, ?)", [str(map_id), str(ctx.author.id)]])

    @commands.command(name="abandon", brief="Abandon the mapset and untrack", description="")
    async def abandon(self, ctx):
        guild_archive_category_id = db.query(["SELECT value FROM config "
                                              "WHERE setting = ? AND parent = ?",
                                              ["guild_archive_category", str(ctx.guild.id)]])
        if not guild_archive_category_id:
            await ctx.send("no archive category set for this server")
            return None

        mapset_owner_check = db.query(["SELECT * FROM mapset_channels "
                                       "WHERE user_id = ? AND channel_id = ?",
                                       [str(ctx.author.id), str(ctx.channel.id)]])
        is_mapset_channel = db.query(["SELECT * FROM mapset_channels "
                                      "WHERE channel_id = ?",
                                      [str(ctx.channel.id)]])
        if (mapset_owner_check or await permissions.is_admin(ctx)) and is_mapset_channel:
            try:
                db.query(["DELETE FROM mod_tracking "
                          "WHERE channel_id = ?",
                          [str(ctx.channel.id)]])
                db.query(["DELETE FROM mod_posts "
                          "WHERE channel_id = ?",
                          [str(ctx.channel.id)]])
                await ctx.send("untracked everything in this channel")

                archive_category = self.bot.get_channel(int(guild_archive_category_id[0][0]))
                await ctx.channel.edit(reason="mapset abandoned", category=archive_category)
                await ctx.send("moved to archive")
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.send("%s this is not your mapset channel" % ctx.author.mention)

    @commands.command(name="set_id", brief="Set a mapset id for this channel",
                      description="Useful if you created this channel without setting an id")
    async def set_mapset_id(self, ctx, mapset_id: str):
        mapset_owner_check = db.query(["SELECT * FROM mapset_channels "
                                       "WHERE user_id = ? AND channel_id = ?",
                                       [str(ctx.author.id), str(ctx.channel.id)]])
        if not (mapset_owner_check or await permissions.is_admin(ctx)):
            return None

        if not mapset_id.isdigit():
            await ctx.send("mapset id must be all numbers")
            return None

        try:
            mapset = await osu.get_beatmapset(s=mapset_id)
            if not mapset:
                await ctx.send("I can't find any mapset with that id")
                return None
        except:
            await ctx.send("i have connection issues with osu servers "
                           "so i can't verify if the id you specified is legit")
            return None

        db.query(["UPDATE mapset_channels "
                  "SET mapset_id = ? WHERE channel_id = ?;",
                  [str(mapset.id), str(ctx.channel.id)]])
        await ctx.send("mapset id updated for this channel")

    @commands.command(name="set_owner", brief="Transfer set ownership to another discord account",
                      description="user_id can only be that discord account's id")
    async def set_owner_id(self, ctx, user_id: str):
        mapset_owner_check = db.query(["SELECT * FROM mapset_channels "
                                       "WHERE user_id = ? AND channel_id = ?",
                                       [str(ctx.author.id), str(ctx.channel.id)]])
        if not (mapset_owner_check or await permissions.is_admin(ctx)):
            return None

        if not user_id.isdigit():
            await ctx.send("user_id must be all numbers")
            return None

        member = ctx.guild.get_member(int(user_id))
        if member:
            db.query(["UPDATE mapset_channels "
                      "SET user_id = ? WHERE channel_id = ?;",
                      [str(user_id), str(ctx.channel.id)]])
            await ctx.channel.set_permissions(target=member, overwrite=self.mapset_owner_default_permissions)
            await ctx.send("mapset owner updated for this channel")

    @commands.command(name="list_mapset_channels", brief="List all mapset channel", description="")
    @commands.check(permissions.is_admin)
    async def list_mapset_channels(self, ctx):
        for channel in db.query("SELECT * FROM mapset_channels"):
            await ctx.send("channel_id <#%s> | role_id %s | user_id <@%s> | mapset_id %s | guild_id %s " % channel)

    @commands.command(name="nuke", brief="Nuke a requested mapset channel", description="")
    @commands.check(permissions.is_admin)
    async def nuke(self, ctx):
        role_id = db.query(["SELECT role_id FROM mapset_channels "
                            "WHERE channel_id = ?",
                            [str(ctx.channel.id)]])
        if role_id:
            try:
                await ctx.send("nuking channel and role in 2 seconds! untracking also")
                await asyncio.sleep(2)
                role = discord.utils.get(ctx.guild.roles, id=int(role_id[0][0]))

                db.query(["DELETE FROM mod_tracking "
                          "WHERE channel_id = ?",
                          [str(ctx.channel.id)]])
                db.query(["DELETE FROM mod_posts "
                          "WHERE channel_id = ?",
                          [str(ctx.channel.id)]])
                await ctx.send("untracked")
                await asyncio.sleep(2)

                db.query(["DELETE FROM mapset_channels "
                          "WHERE channel_id = ?",
                          [str(ctx.channel.id)]])
                await role.delete(reason="manually nuked the role due to abuse")
                await ctx.channel.delete(reason="manually nuked the channel due to abuse")
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.send("this is not a mapset channel")

    @commands.command(name="request_mapset_channel",
                      brief="Request a mapset channel",
                      description="")
    async def make_mapset_channel(self, ctx, mapset_id="0", *, mapset_title=None):
        guild_mapset_category_id = db.query(["SELECT value FROM config "
                                             "WHERE setting = ? AND parent = ?",
                                             ["guild_mapset_category", str(ctx.guild.id)]])

        if not mapset_id.isdigit():
            await ctx.send("first argument must be a number")
            return

        if not guild_mapset_category_id:
            await ctx.send("Not enabled in this server yet.")
            return

        await ctx.send("sure, gimme a moment")

        if mapset_id == "0":
            mapset = None
        else:
            try:
                mapset = await osu.get_beatmapset(s=mapset_id)
                if not mapset:
                    await ctx.send("you specified incorrect mapset id. "
                                   "you can correct this with `'set_id` command in the mapset channel")
            except Exception as e:
                mapset = None
                print(e)
                await ctx.send("looks like there are connection issues to osu servers, "
                               "so i'll put in a blank value for the mapset_id "
                               "and later you can update it with `'set_id` command")

        if mapset:
            mapset_id = str(mapset.id)
            channel_topic = str(mapset.url)
        else:
            mapset_id = "0"
            channel_topic = ""

        if mapset_title:
            discord_friendly_channel_name = mapset_title.replace(" ", "_").lower()
            role_name = mapset_title
        elif mapset:
            discord_friendly_channel_name = mapset.title.replace(" ", "_").lower()
            role_name = mapset.title
        else:
            await ctx.send("i was unable to create a mapset channel for you because "
                           "you neither specified a valid mapset_id of your mapset (or there are connection issues) "
                           "nor a mapset name. "
                           "i need at least one to make a mapset channel.")
            return

        guild = ctx.guild
        role_color = discord.Colour(random.randint(1, 16777215))
        mapset_role = await guild.create_role(name=role_name, colour=role_color, mentionable=True)
        category = self.bot.get_channel(int(guild_mapset_category_id[0][0]))
        channel_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: self.mapset_owner_default_permissions,
            mapset_role: discord.PermissionOverwrite(read_messages=True),
            guild.me: self.mapset_bot_default_permissions
        }
        channel = await guild.create_text_channel(discord_friendly_channel_name,
                                                  overwrites=channel_overwrites,
                                                  category=category,
                                                  topic=channel_topic)
        await ctx.author.add_roles(mapset_role)
        await channel.send(content="%s done!" % ctx.author.mention,
                           embed=await self.docs.mapset_channel_management())
        db.query(["INSERT INTO mapset_channels "
                  "VALUES (?, ?, ?, ?, ?)",
                  [str(channel.id), str(mapset_role.id), str(ctx.author.id), str(mapset_id), str(ctx.guild.id)]])
        await ctx.send("ok, i'm done!")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, deleted_channel):
        try:
            db.query(["DELETE FROM mapset_channels WHERE channel_id = ?", [str(deleted_channel.id)]])
            db.query(["DELETE FROM mod_tracking WHERE channel_id = ?", [str(deleted_channel.id)]])
            db.query(["DELETE FROM mod_posts WHERE channel_id = ?", [str(deleted_channel.id)]])
            print("channel %s is deleted" % deleted_channel.name)
        except Exception as e:
            print(e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        mapsets_user_is_in = db.query(["SELECT channel_id, role_id FROM mapset_channels "
                                       "WHERE user_id = ?",
                                       [str(member.id)]])
        if mapsets_user_is_in:
            for mapset in mapsets_user_is_in:
                channel = self.bot.get_channel(int(mapset[0]))
                if channel:
                    role = discord.utils.get(channel.guild.roles, id=int(mapset[1]))
                    await member.add_roles(role, reason="set owner returned")
                    await channel.set_permissions(target=member, overwrite=self.mapset_owner_default_permissions)
                    await channel.send("the mapset owner has returned. "
                                       "next time you track the mapset, it will be unarchived, "
                                       "unless this is already ranked. either way, permissions restored.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        mapsets_user_is_in = db.query(["SELECT channel_id FROM mapset_channels "
                                       "WHERE user_id = ?",
                                       [str(member.id)]])
        if mapsets_user_is_in:
            for mapset in mapsets_user_is_in:
                channel = self.bot.get_channel(int(mapset[0]))
                if channel:
                    await channel.send("the mapset owner has left the server")
                    db.query(["DELETE FROM mod_tracking WHERE channel_id = ?", [str(channel.id)]])
                    db.query(["DELETE FROM mod_posts WHERE channel_id = ?", [str(channel.id)]])
                    await channel.send("untracked everything in this channel")
                    guild_archive_category_id = db.query(["SELECT value FROM config "
                                                          "WHERE setting = ? AND parent = ?",
                                                          ["guild_archive_category", str(channel.guild.id)]])
                    if guild_archive_category_id:
                        archive_category = self.bot.get_channel(int(guild_archive_category_id[0][0]))
                        await channel.edit(reason=None, category=archive_category)
                        await channel.send("channel archived")


def setup(bot):
    bot.add_cog(MapsetChannel(bot))
