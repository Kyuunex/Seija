from modules import dbhandler
from modules import docs
from modules import permissions
import discord
import asyncio

async def make_queue_channel(client, ctx, queuetype):
    guildqueuecategory = await dbhandler.query(["SELECT value FROM config WHERE setting = ? AND parent = ?", ["guildqueuecategory", str(ctx.guild.id)]])
    if guildqueuecategory:
        if not await dbhandler.query(["SELECT discordid FROM queues WHERE discordid = ? AND guildid = ?", [str(ctx.message.author.id), str(ctx.guild.id)]]):
            try:
                await ctx.send("sure, gimme a moment")
                if not queuetype:
                    queuetype = "std"
                guild = ctx.message.guild
                channeloverwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.message.author: discord.PermissionOverwrite(
                        create_instant_invite=True,
                        manage_channels=True,
                        manage_roles=True,
                        read_messages=True,
                        send_messages=True,
                        manage_messages=True,
                        embed_links=True,
                        attach_files=True,
                        read_message_history=True,
                    ),
                    guild.me: discord.PermissionOverwrite(
                        manage_channels=True,
                        manage_roles=True,
                        read_messages=True,
                        send_messages=True,
                        embed_links=True
                    )
                }
                discordfriendlychannelname = "%s-%s-queue" % (
                    ctx.message.author.display_name.replace(" ", "_").lower(), queuetype)
                category = client.get_channel(int(guildqueuecategory[0][0]))
                channel = await guild.create_text_channel(discordfriendlychannelname, overwrites=channeloverwrites, category=category)
                await dbhandler.query(["INSERT INTO queues VALUES (?, ?, ?)", [str(channel.id), str(ctx.message.author.id), str(ctx.guild.id)]])
                await channel.send("%s done!" % (ctx.message.author.mention), embed=await docs.queuemanagement())
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.send("you already have a queue though. or it was deleted, in this case, ping kyuunex")
    else:
        await ctx.send("Not enabled in this server yet.")


async def queuesettings(client, ctx, action, embed_title = None, embed_desc = None):
    if (await dbhandler.query(["SELECT discordid FROM queues WHERE discordid = ? AND channelid = ?", [str(ctx.message.author.id), str(ctx.message.channel.id)]])) or (await permissions.check(ctx.message.author.id)):
        try:
            if embed_title:
                embed = discord.Embed(title=embed_title, color=0xbd3661, description=embed_desc)
                embed.set_author(name=ctx.message.author.display_name, icon_url=ctx.message.author.avatar_url)
                await ctx.message.delete()
            else:
                embed = None
            if action == "open":
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=None, send_messages=True)
                await ctx.send("queue open!", embed=embed)
            elif action == "close":
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=None, send_messages=False)
                await ctx.send("queue closed!", embed=embed)
            elif action == "hide":
                await ctx.message.channel.set_permissions(ctx.message.guild.default_role, read_messages=False, send_messages=False)
                await ctx.send("queue hidden!")
        except Exception as e:
            await ctx.send(e)
    else:
        await ctx.message.delete()
        await ctx.send("%s not your queue" % (ctx.message.author.mention), delete_after=3)
