from seija.cogs.Docs import Docs
from seija.modules import permissions
from seija.reusables import exceptions
from seija.reusables import get_member_helpers
from seija.reusables import send_large_message
import discord
from discord.ext import commands
import random
import asyncio
from seija.embeds import oldembeds as osuembed


class MapsetChannel(commands.Cog):
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
        self.mapset_bot_default_permissions = discord.PermissionOverwrite(
            manage_channels=True,
            manage_roles=True,
            read_messages=True,
            send_messages=True,
            embed_links=True
        )

    @commands.command(name="debug_mapset_force_call_on_member_join", brief="Restore mapset channel perms to a user.")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def debug_mapset_force_call_on_member_join(self, ctx, user_id):
        """
        A debug command that is used to manually restore mapset channel permissions
        to a user who left and maybe returned with a different account.
        """

        member = get_member_helpers.get_member_guaranteed(ctx, user_id)
        if not member:
            await ctx.send("no member found with that name")
            return

        await self.on_member_join(member)
        await ctx.send("done")

    @commands.command(name="show_mapset_members", brief="Print out a list of members who are in this mapset")
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def show_mapset_members(self, ctx):
        """
        This command print out members who have the role that is tied to this mapset channel.
        """

        async with self.bot.db.execute("SELECT role_id FROM mapset_channels WHERE user_id = ? AND channel_id = ?",
                                       [int(ctx.author.id), int(ctx.channel.id)]) as cursor:
            role_id_list = await cursor.fetchone()
        if not role_id_list:
            await ctx.send("not your mapset channel")
            return

        role = ctx.guild.get_role(int(role_id_list[0]))

        if not role:
            await ctx.reply("Looks like the role for this mapset channel no longer exists.")
            return

        buffer = ""
        for member in role.members:
            buffer += f"{member.display_name}\n"

        embed = discord.Embed(color=0xadff2f)
        embed.set_author(name="Mapset members")
        await send_large_message.send_large_embed(ctx.channel, embed, buffer)

    @commands.command(name="add", brief="Add a user in the current mapset channel")
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def add(self, ctx, *, user_name: str):
        """
        This command is used to add a Discord account into a Mapset Channel.
        """

        async with self.bot.db.execute("SELECT role_id FROM mapset_channels WHERE user_id = ? AND channel_id = ?",
                                       [int(ctx.author.id), int(ctx.channel.id)]) as cursor:
            role_id_list = await cursor.fetchone()
        if not role_id_list:
            await ctx.send("not your mapset channel")
            return

        member = get_member_helpers.get_member_guaranteed(ctx, user_name)
        if not member:
            await ctx.send("No member found with what you specified. Try using a Discord account ID.")
            return

        role = ctx.guild.get_role(int(role_id_list[0]))
        if not role:
            await ctx.reply("Looks like the role for this mapset channel no longer exists.")
            return

        try:
            await member.add_roles(role, reason="added to mapset")
            await ctx.send(f"added {member.mention} in this channel")
        except discord.Forbidden:
            await ctx.reply("I do not have permissions to add roles.")

    @commands.command(name="remove", brief="Remove a user from the current mapset channel")
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def remove(self, ctx, *, user_name: str):
        """
        This command is used to remove a Discord account from a Mapset Channel.
        """

        async with self.bot.db.execute("SELECT role_id FROM mapset_channels WHERE user_id = ? AND channel_id = ?",
                                       [int(ctx.author.id), int(ctx.channel.id)]) as cursor:
            role_id_list = await cursor.fetchone()
        if not role_id_list:
            await ctx.send("not your mapset channel")
            return

        member = get_member_helpers.get_member_guaranteed(ctx, user_name)
        if not member:
            await ctx.send("No member found with what you specified. Try using a Discord account ID.")
            return

        role = ctx.guild.get_role(int(role_id_list[0]))
        if not role:
            await ctx.reply("Looks like the role for this mapset channel no longer exists.")
            return

        try:
            await member.remove_roles(role, reason="removed from mapset")
            await ctx.send(f"removed {member.mention} from this channel")
        except discord.Forbidden:
            await ctx.reply("I do not have permissions to remove roles.")

    @commands.command(name="claim_diff", brief="Claim a beatmapset difficulty")
    @commands.guild_only()
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def claim_diff(self, ctx, *, map_id):
        """
        This command is used to claim a beatmap difficulty.
        This command is a placeholder at this point in time.
        """

        await self.bot.db.execute("INSERT INTO difficulty_claims VALUES (?, ?)", [int(map_id), int(ctx.author.id)])
        await self.bot.db.commit()
        await ctx.send("done")

    @commands.command(name="abandon", brief="Abandon the mapset and untrack")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def abandon(self, ctx):
        """
        This command is used to untrack everything from a mapset channel
        and move the channel to an archive category
        """

        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       ["mapset_archive", int(ctx.guild.id)]) as cursor:
            guild_archive_category_id = await cursor.fetchone()
        if not guild_archive_category_id:
            await ctx.send("no archive category set for this server")
            return

        async with self.bot.db.execute("SELECT user_id FROM mapset_channels WHERE user_id = ? AND channel_id = ?",
                                       [int(ctx.author.id), int(ctx.channel.id)]) as cursor:
            mapset_owner_check = await cursor.fetchone()

        async with self.bot.db.execute("SELECT mapset_id FROM mapset_channels WHERE channel_id = ?",
                                       [int(ctx.channel.id)]) as cursor:
            is_mapset_channel = await cursor.fetchone()

        if not is_mapset_channel:
            await ctx.send("This is not a mapset channel")
            return

        if not (mapset_owner_check or await permissions.is_admin(ctx)):
            await ctx.send(f"{ctx.author.mention} this is not your mapset channel")
            return

        await self.bot.db.execute("DELETE FROM mod_tracking WHERE channel_id = ?", [int(ctx.channel.id)])
        await self.bot.db.execute("DELETE FROM mod_post_history WHERE channel_id = ?", [int(ctx.channel.id)])
        await self.bot.db.commit()
        await ctx.send("untracked everything in this channel")

        try:
            archive_category = self.bot.get_channel(int(guild_archive_category_id[0]))
            await ctx.channel.edit(reason="mapset abandoned", category=archive_category)
            await ctx.send("moved to archive")
        except Exception as e:
            await ctx.send(embed=await exceptions.embed_exception(e))

    @commands.command(name="set_id", brief="Set a mapset id for this channel")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def set_mapset_id(self, ctx, mapset_id: str):
        """
        Manually set a mapset ID to a Mapset Channel.
        Useful if you created this channel without setting an ID.
        """

        async with self.bot.db.execute("SELECT user_id FROM mapset_channels WHERE user_id = ? AND channel_id = ?",
                                       [int(ctx.author.id), int(ctx.channel.id)]) as cursor:
            mapset_owner_check = await cursor.fetchone()
        if not (mapset_owner_check or await permissions.is_admin(ctx)):
            return

        if not mapset_id.isdigit():
            await ctx.send("mapset id must be all numbers")
            return

        try:
            mapset = await self.bot.osu.get_beatmapset(s=mapset_id)
            if not mapset:
                await ctx.send("I can't find any mapset with that id")
                return
        except Exception as e:
            await ctx.send("i have connection issues with osu servers "
                           "so i can't verify if the id you specified is legit. "
                           "try again later", embed=await exceptions.embed_exception(e))
            return

        await self.bot.db.execute("UPDATE mapset_channels SET mapset_id = ? WHERE channel_id = ?",
                                  [int(mapset.id), int(ctx.channel.id)])
        await self.bot.db.commit()

        embed = await osuembed.beatmapset(mapset)

        await ctx.send("mapset id updated for this channel, with id of this set", embed=embed)

    @commands.command(name="set_owner", brief="Transfer set ownership to another discord account")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def set_owner_id(self, ctx, user_id: str):
        """
        Transfer the Mapset Channel ownership to another Discord account.
        user_id can only be that discord account's id
        """
        async with self.bot.db.execute("SELECT user_id FROM mapset_channels WHERE user_id = ? AND channel_id = ?",
                                       [int(ctx.author.id), int(ctx.channel.id)]) as cursor:
            mapset_owner_check = await cursor.fetchone()
        if not (mapset_owner_check or await permissions.is_admin(ctx)):
            return

        if not user_id.isdigit():
            await ctx.send("user_id must be all numbers")
            return

        member = ctx.guild.get_member(int(user_id))
        if not member:
            await ctx.send("I can't find a member with that mapset ID")
            return

        await self.bot.db.execute("UPDATE mapset_channels SET user_id = ? WHERE channel_id = ?",
                                  [int(user_id), int(ctx.channel.id)])
        await self.bot.db.commit()

        await ctx.channel.set_permissions(target=member, overwrite=self.mapset_owner_default_permissions)
        await ctx.send("mapset owner updated for this channel")

    @commands.command(name="list_mapset_channels", brief="List all mapset channel")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    async def list_mapset_channels(self, ctx):
        """
        Send an embed that contains information about all Mapset channels in my database
        """

        buffer = ""

        async with self.bot.db.execute("SELECT channel_id, role_id, user_id, mapset_id, guild_id "
                                       "FROM mapset_channels") as cursor:
            mapset_channels = await cursor.fetchall()
        if not mapset_channels:
            buffer += "no mapset channels in my database"

        for channel in mapset_channels:
            buffer += "channel_id <#%s> | role_id %s | user_id <@%s> | mapset_id %s | guild_id %s \n" % channel
            buffer += "\n"

        embed = discord.Embed(color=0xff6781)

        await send_large_message.send_large_embed(ctx.channel, embed, buffer)

    @commands.command(name="nuke", brief="Nuke a mapset channel")
    @commands.check(permissions.is_admin)
    @commands.check(permissions.is_not_ignored)
    @commands.guild_only()
    async def nuke(self, ctx):
        """
        Nuke a requested mapset channel.
        This will untrack everything, delete the channel and the role.
        """

        async with self.bot.db.execute("SELECT role_id FROM mapset_channels WHERE channel_id = ?",
                                       [int(ctx.channel.id)]) as cursor:
            role_id = await cursor.fetchone()
        if not role_id:
            await ctx.send("this is not a mapset channel")
            return

        try:
            await ctx.send("nuking channel and role in 2 seconds! untracking also")
            await asyncio.sleep(2)
            role = ctx.guild.get_role(int(role_id[0]))

            await self.bot.db.execute("DELETE FROM mod_tracking WHERE channel_id = ?", [int(ctx.channel.id)])
            await self.bot.db.execute("DELETE FROM mod_post_history WHERE channel_id = ?", [int(ctx.channel.id)])
            await ctx.send("untracked")
            await asyncio.sleep(2)

            await self.bot.db.execute("DELETE FROM mapset_channels WHERE channel_id = ?", [int(ctx.channel.id)])
            await self.bot.db.commit()
            await role.delete(reason="manually nuked the role due to abuse")
            await ctx.channel.delete(reason="manually nuked the channel due to abuse")
        except Exception as e:
            await ctx.send(embed=await exceptions.embed_exception(e))

    @commands.command(name="request_mapset_channel", brief="Request a mapset channel")
    @commands.guild_only()
    @commands.check(permissions.is_not_ignored)
    async def make_mapset_channel(self, ctx, mapset_id="0", *, mapset_title=None):
        """
        This command allows a user to request a mapset channel.
        For this command to work, I either need a mapset_id, or a mapset title or both,
        """

        async with self.bot.db.execute("SELECT category_id FROM categories WHERE setting = ? AND guild_id = ?",
                                       ["mapset", int(ctx.guild.id)]) as cursor:
            guild_mapset_category_id = await cursor.fetchone()

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
                mapset = await self.bot.osu.get_beatmapset(s=mapset_id)
                if not mapset:
                    await ctx.send("you specified incorrect mapset id. "
                                   "you can correct this with `.set_id` command in the mapset channel")
                if int(mapset.approved) == 1 or int(mapset.approved) == 2:
                    await ctx.send("This map is ranked, you are not supposed to make a channel for it")
                    return
            except Exception as e:
                mapset = None
                print(e)
                await ctx.send("looks like there are connection issues to osu servers, "
                               "so i'll put in a blank value for the mapset_id "
                               "and later you can update it with `.set_id` command")

        if mapset:
            mapset_id = int(mapset.id)
            channel_topic = str(mapset.url)
        else:
            mapset_id = 0
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
        category = self.bot.get_channel(int(guild_mapset_category_id[0]))
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
        await channel.send(content=f"{ctx.author.mention} done! Please keep in mind that "
                                   f"I don't automatically start tracking. "
                                   "You can use the `.track` command bellow to start tracking.",
                           embed=await Docs.mapset_channel_management())
        await self.bot.db.execute("INSERT INTO mapset_channels VALUES (?, ?, ?, ?, ?)",
                                  [int(channel.id), int(mapset_role.id), int(ctx.author.id), int(mapset_id),
                                   int(ctx.guild.id)])
        await self.bot.db.commit()
        await ctx.send("ok, i'm done!")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, deleted_channel):
        try:
            await self.bot.db.execute("DELETE FROM mapset_channels WHERE channel_id = ?", [int(deleted_channel.id)])
            await self.bot.db.execute("DELETE FROM mod_tracking WHERE channel_id = ?", [int(deleted_channel.id)])
            await self.bot.db.execute("DELETE FROM mod_post_history WHERE channel_id = ?", [int(deleted_channel.id)])
            await self.bot.db.commit()
            print(f"channel {deleted_channel.name} is deleted, "
                  f"just in case it's a mapset channel, i'll ran sql commands")
        except Exception as e:
            print(e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with self.bot.db.execute("SELECT channel_id, role_id FROM mapset_channels "
                                       "WHERE user_id = ? AND guild_id = ?",
                                       [int(member.id), int(member.guild.id)]) as cursor:
            mapsets_user_is_in = await cursor.fetchall()
        if not mapsets_user_is_in:
            return

        for mapset in mapsets_user_is_in:
            channel = self.bot.get_channel(int(mapset[0]))
            if not channel:
                # if this is the case, the channel may have been deleted but there's still a DB record of it????
                continue

            role = channel.guild.get_role(int(mapset[1]))
            if not role:
                # if this is the case, the role may have been deleted but there's still a DB record of it????
                continue

            await member.add_roles(role, reason="set owner returned")
            await channel.set_permissions(target=member, overwrite=self.mapset_owner_default_permissions)
            await channel.send("the mapset owner has returned. "
                               "next time you track the mapset, it will be unarchived, "
                               "unless this is already ranked. either way, permissions restored.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        async with self.bot.db.execute("SELECT channel_id FROM mapset_channels WHERE user_id = ? AND guild_id = ?",
                                       [int(member.id), int(member.guild.id)]) as cursor:
            mapsets_user_is_in = await cursor.fetchall()
        if not mapsets_user_is_in:
            return

        for mapset in mapsets_user_is_in:
            channel = self.bot.get_channel(int(mapset[0]))
            if not channel:
                continue

            await channel.send("the mapset owner has left the server")
            await self.bot.db.execute("DELETE FROM mod_tracking WHERE channel_id = ?", [int(channel.id)])
            await self.bot.db.execute("DELETE FROM mod_post_history WHERE channel_id = ?", [int(channel.id)])
            await self.bot.db.commit()
            await channel.send("untracked everything in this channel")

            async with self.bot.db.execute("SELECT category_id FROM categories "
                                           "WHERE setting = ? AND guild_id = ?",
                                           ["mapset_archive", int(channel.guild.id)]) as cursor:
                guild_archive_category_id = await cursor.fetchone()
            if not guild_archive_category_id:
                continue

            archive_category = self.bot.get_channel(int(guild_archive_category_id[0]))
            await channel.edit(reason=None, category=archive_category)
            await channel.send("channel archived")


async def setup(bot):
    await bot.add_cog(MapsetChannel(bot))
