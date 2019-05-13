from modules import dbhandler
from modules import osuapi
from modules import docs
from modules import permissions
import discord
import random
import asyncio


async def make_mapset_channel(client, ctx, mapset_id, mapsetname):
    guildmapsetcategory = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_mapset_category", str(ctx.guild.id)]])
    if guildmapsetcategory:
        try:
            await ctx.send("sure, gimme a moment")
            if int(mapset_id) == 0 or mapset_id == None:
                mapset = None
                mapset_id = "0"
                #desc = ""
            else:
                mapset = await osuapi.get_beatmap(mapset_id)
                mapset_id = str(mapset_id)
                #desc = "https://osu.ppy.sh/beatmapsets/%s" % (mapset_id)

            if mapsetname:
                discordfriendlychannelname = mapsetname.replace(
                    " ", "_").lower()
                rolename = mapsetname
            elif mapset:
                discordfriendlychannelname = mapset['title'].replace(
                    " ", "_").lower()
                rolename = mapset['title']
            else:
                discordfriendlychannelname = None
                rolename = None

            if discordfriendlychannelname:
                guild = ctx.message.guild
                rolecolor = discord.Colour(random.randint(1, 16777215))
                mapsetrole = await guild.create_role(name=rolename, colour=rolecolor, mentionable=True)
                category = client.get_channel(int(guildmapsetcategory[0][0]))
                channeloverwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.message.author: discord.PermissionOverwrite(
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
                    ),
                    mapsetrole: discord.PermissionOverwrite(read_messages=True),
                    guild.me: discord.PermissionOverwrite(
                        manage_channels=True,
                        read_messages=True,
                        send_messages=True,
                        embed_links=True
                    )
                }
                channel = await guild.create_text_channel(discordfriendlychannelname, overwrites=channeloverwrites, category=category)
                await ctx.message.author.add_roles(mapsetrole)
                await channel.send("%s done!" % (ctx.message.author.mention), embed=await docs.mapchannelmanagement())
                await dbhandler.query(["INSERT INTO mapset_channels VALUES (?, ?, ?, ?, ?)", [str(channel.id), str(mapsetrole.id), str(ctx.message.author.id), str(mapset_id), str(ctx.guild.id)]])
            else:
                await ctx.send("You are not using this command correctly")
        except Exception as e:
            print(e)
            await ctx.send("This did not work. You probably specified something incorrectly. Look at the instructions carefully.")
    else:
        await ctx.send("Not enabled in this server yet.")


async def mapset_channelsettings(client, ctx, action, user_id):
    role_idlist = await dbhandler.query(["SELECT role_id FROM mapset_channels WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])
    if role_idlist:
        try:
            member = ctx.guild.get_member(int(user_id))
            role = discord.utils.get(ctx.guild.roles, id=int(role_idlist[0][0]))
            if action == "add":
                await member.add_roles(role, reason="added to mapset")
                await ctx.send("added %s in this channel" % (member.mention))
            elif action == "remove":
                await member.remove_roles(role, reason="removed from mapset")
                await ctx.send("removed %s from this channel" % (member.mention))
        except Exception as e:
            await ctx.send(e)
    else:
        await ctx.send("not your mapset channel")


async def nuke_mapset_channel(client, ctx):
    role_idlist = await dbhandler.query(["SELECT role_id FROM mapset_channels WHERE channel_id = ?", [str(ctx.message.channel.id)]])
    if role_idlist:
        try:
            await ctx.send("nuking channel and role in 2 seconds! untracking also")
            await asyncio.sleep(2)
            role = discord.utils.get(ctx.guild.roles, id=int(role_idlist[0][0]))

            mapset_id = await dbhandler.query(["SELECT mapset_id FROM mod_tracking WHERE channel_id = ?", [str(ctx.message.channel.id)]])
            if mapset_id:
                await dbhandler.query(["DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",[str(mapset_id[0][0]), str(ctx.message.channel.id)]])
                await dbhandler.query(["DELETE FROM mod_posts WHERE mapset_id = ? AND channel_id = ?",[str(mapset_id[0][0]), str(ctx.message.channel.id)]])
                await ctx.send("untracked")
                await asyncio.sleep(2)

            await dbhandler.query(["DELETE FROM mapset_channels WHERE channel_id = ?", [str(ctx.message.channel.id)]])
            await role.delete(reason="Manually nuked the role due to abuse")
            await ctx.message.channel.delete(reason="Manually nuked the channel due to abuse")
        except Exception as e:
            await ctx.send(e)
    else:
        await ctx.send("this is not a mapset channel")


async def abandon(client, ctx):
    guildarchivecategory = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guild_archive_category", str(ctx.guild.id)]])
    if guildarchivecategory:
        if (await dbhandler.query(["SELECT * FROM mapset_channels WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (await dbhandler.query(["SELECT * FROM queues WHERE user_id = ? AND channel_id = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (await permissions.check(ctx.message.author.id)):
            try:
                mapset_id = await dbhandler.query(["SELECT mapset_id FROM mod_tracking WHERE channel_id = ?", [str(ctx.message.channel.id)]])
                if mapset_id:
                    await dbhandler.query(["DELETE FROM mod_tracking WHERE mapset_id = ? AND channel_id = ?",[str(mapset_id[0][0]), str(ctx.message.channel.id)]])
                    await dbhandler.query(["DELETE FROM mod_posts WHERE mapset_id = ? AND channel_id = ?",[str(mapset_id[0][0]), str(ctx.message.channel.id)]])
                    await ctx.send("untracked")
                    await asyncio.sleep(1)

                archivecategory = client.get_channel(int(guildarchivecategory[0][0]))
                await ctx.message.channel.edit(reason=None, category=archivecategory)
                await ctx.send("Abandoned and moved to archive")
            except Exception as e:
                await ctx.send(e)
    else:
        await ctx.send("no archive category set for this server")