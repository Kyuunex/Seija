import discord
from discord.ext import commands
from modules import permissions


class Docs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="docs", brief="A friendlier looking help command.")
    @commands.check(permissions.is_not_ignored)
    async def docs(self, ctx, sub_help=None):
        """
        A custom help command written to look more friendly to end users.
        """

        if sub_help == "veto":
            async with self.bot.db.execute("SELECT channel_id FROM channels "
                                           "WHERE setting = ? AND channel_id = ?",
                                           ["veto", str(ctx.channel.id)]) as cursor:
                is_veto_channel = await cursor.fetchone()
            if not is_veto_channel:
                embed = await self.main(ctx)
            else:
                embed = await self.veto()
        elif sub_help == "mapset_channel":
            embed = await Docs.mapset_channel()
        elif sub_help == "queue":
            embed = await Docs.queue(ctx.author)
        elif sub_help == "mapset_channel_management":
            embed = await Docs.mapset_channel_management()
        elif sub_help == "queue_management":
            embed = await Docs.queue_management()
        else:
            embed = await self.main(ctx)

        embed.set_thumbnail(url="https://i.imgur.com/JhL9PV8.png")
        # embed.set_author(name="Seija", icon_url="https://i.imgur.com/1icHC5a.png")
        embed.set_footer(text="Made by Kyuunex", icon_url="https://avatars0.githubusercontent.com/u/5400432")

        await ctx.send(embed=embed)

    async def main(self, ctx):
        embed = discord.Embed(title="Seija teaches you how to be a bot master.",
                              description="Any abuse will be dealt with punishment.",
                              color=0xbd3661)
        embed.add_field(name=".docs mapset_channel",
                        value="Show a help menu for requesting a mapset channel.",
                        inline=False)
        embed.add_field(name=".docs queue",
                        value="Show a help menu for requesting a queue channel.",
                        inline=False)
        embed.add_field(name=".docs mapset_channel_management",
                        value="Show mapset channel management commands.",
                        inline=False)
        embed.add_field(name=".docs queue_management",
                        value="Show queue channel management commands.",
                        inline=False)

        async with self.bot.db.execute("SELECT channel_id FROM channels WHERE setting = ? AND channel_id = ?",
                                       ["veto", str(ctx.channel.id)]) as cursor:
            is_veto_channel = await cursor.fetchone()
        if is_veto_channel:
            embed.add_field(name=".docs veto",
                            value="Commands for tracking a mapset in veto mode.",
                            inline=True)

        embed.add_field(name=".from (country_name)",
                        value="Retrieve a list of server members who are from the specified country. "
                              "Takes Alpha-2, Alpha-3 codes and full country names.",
                        inline=False)
        embed.add_field(name=".demographics",
                        value="Show server demographics. "
                              "Shows how many members are from which country and the percentage of them.",
                        inline=False)
        embed.add_field(name=".ts (mod)",
                        value="Send a clickable timestamp for the osu! editor. "
                              "The message must start with a timestamp.",
                        inline=False)
        return embed

    @staticmethod
    async def veto():
        embed = discord.Embed(title="~~BNS PLS MUTUAL ME~~",
                              description="**Veto tracking commands:**",
                              color=0xbd3661)
        embed.add_field(name=".veto <mapset_id>",
                        value="Track a mapset in this channel in veto mode.",
                        inline=False)
        embed.add_field(name=".unveto <mapset_id>",
                        value="Untrack a mapset in this channel in veto mode.",
                        inline=False)

        return embed

    @staticmethod
    async def queue(author):
        channel_friendly_author = author.display_name.replace(" ", "_").lower()

        text = "**__Queue creation command:__**\n"
        text += "`.request_queue (queue type)` - Create a modding queue. \n"
        text += "By default, the queue will be closed.\n"
        text += "`(queue type)` is an optional argument that specifies "
        text += "what goes between your username and the word `queue` in the title of the channel. \n"
        text += "If no argument is supplied, `std` will be filled automatically. \n"
        text += "Please follow our naming standards.\n"
        text += "\n"
        text += "**__Examples:__**\n"
        text += f"`.request_queue` - This example will create `#{channel_friendly_author}-std-queue`\n"
        text += f"`.request_queue mania` - This example will create `#{channel_friendly_author}-mania-queue`\n"
        text += f"`.request_queue taiko-bn` - This example will create `#{channel_friendly_author}-taiko-bn-queue`\n"
        text += "\n"
        text += "For queue management commands, type `.docs queue_management`\n"
        text += "\n"
        text += "**Remember:**\n"
        text += "**__Do not__ create a queue __only__ for GD requests.**\n"
        text += "**__It should__ be a modding queue, not a diary and not an image dump. \n"
        text += "You can be creative and do other things but its primary purpose must be a modding queue.**\n"

        embed = discord.Embed(title="With this command you can create a queue channel.",
                              description=text,
                              color=0xbd3661)

        return embed

    @staticmethod
    async def mapset_channel():
        text = "**__Mapset channel creation command:__**: \n"
        text += "`.request_mapset_channel (mapset id) (song name)` - "
        text += "This is the general command to create a mapset channel.\n"
        text += "`(song name)` is an optional argument that is not required. \n"
        text += "If the mapset is not uploaded yet, `(mapset id)` can be set to `0` "
        text += "but in that case, the `(song name)` argument is required.\n"
        text += "\n"
        text += "**__Examples:__**\n"
        text += "`.request_mapset_channel 817793` - An example usage with mapset ID.\n"
        text += "`.request_mapset_channel 0 Futanari Nari ni` - An example usage with just the song title.\n"
        text += "\n"
        text += "For mapset channel management commands, type `.docs mapset_channel_management`\n"
        text += "\n"
        text += "**Remember:**\n"
        text += "**__Do not__ create a mapset channel for single person sets. **\n"
        text += "**__Do not__ create a channel if you don't have GDers/collaborators ready.**\n"

        embed = discord.Embed(title="With this command you can create a mapset channel for collaborative purposes.",
                              description=text,
                              color=0xbd3661)

        return embed

    @staticmethod
    async def queue_management():
        embed = discord.Embed(title="Queue management commands",
                              description="**Please avoid manually editing channel permissions "
                                          "unless you want to ban a specific person or a role from your queue "
                                          "or the bot is down.**",
                              color=0xbd3661)
        embed.add_field(name=".open",
                        value="Open the queue, everyone can see it and post in it.",
                        inline=False)
        embed.add_field(name=".close",
                        value="Close the queue, everyone can see it but can't post in it. "
                              "You can also use this command to unhide the queue, "
                              "but again, nobody will be able to post in it.",
                        inline=False)
        embed.add_field(name=".hide",
                        value="Hide the queue, only admins can see the queue. Nobody else can see it and post in it.",
                        inline=False)
        embed.add_field(name=".archive",
                        value="Move the queue to the archive category, "
                              "only admins can see the queue. "
                              "Nobody else can see it and post in it.",
                        inline=False)
        embed.add_field(name=".recategorize",
                        value="Move the queue to the correct category "
                              "if you became a BN or have gotten enough kudosu to earn a spot in a higher category. ",
                        inline=False)
        embed.add_field(name=".queue_cleanup",
                        value="Deletes messages that are not made by the queue owner or me or has no beatmap link.",
                        inline=False)
        embed.add_field(name=".add_co_modder",
                        value="Turns a modding queue into a joint one. "
                              "This command allows you to add a co-owner to your queue. "
                              "They will be able to open/close/hide/archive the queue. "
                              "For more info type `.help add_co_modder`.",
                        inline=False)
        embed.add_field(name=".remove_co_modder",
                        value="Remove a co-owner from your queue.",
                        inline=False)
        embed.add_field(name=".get_queue_owner_list",
                        value="List all owners of the queue.",
                        inline=False)
        embed.add_field(name=".give_queue",
                        value="Give your creator permissions of the queue to someone. "
                              "This will clear all co-owners too.",
                        inline=False)

        return embed

    @staticmethod
    async def mapset_channel_management():
        embed = discord.Embed(title="Mapset channel management commands",
                              description="`(user)` can either be the name of the user or a discord account user ID. "
                                          "To get the user ID, "
                                          "you need to enable the developer mode in your discord settings, "
                                          "right click on the user and click \"Copy ID\". "
                                          "Using IDs is recommended rather than names.",
                              color=0xbd3661)
        embed.add_field(name=".add (user)", value="Add a user to the mapset channel.", inline=False)
        embed.add_field(name=".remove (user)", value="Remove a user from the mapset channel.", inline=False)
        embed.add_field(name=".abandon",
                        value="If you're abandoning the set, whether temporarily or permanently, "
                              "this will stop all tracking and move the channel to the archive category.",
                        inline=False)
        embed.add_field(name=".set_id (mapset_id)",
                        value="Set a mapset ID for this channel. "
                              "This is useful if you created this channel without setting an ID.",
                        inline=False)
        embed.add_field(name=".set_owner (user_id)",
                        value="Transfer the mapset ownership to another discord account. "
                              "user_id can only be that discord account's ID.",
                        inline=False)
        embed.add_field(name=".track (tracking_mode)",
                        value="Track the mapset in this channel. "
                              "For (tracking_mode), specify `timeline` for the discussion/timeline type "
                              "or `notification` for the notification type.\n"
                              "timeline mode example: https://i.imgur.com/3pHW9FM.png\n"
                              "notification mode example: https://i.imgur.com/e2LwWh2.png\n",
                        inline=False)
        embed.add_field(name=".untrack", value="Untrack everything in this channel.", inline=False)

        return embed


def setup(bot):
    bot.add_cog(Docs(bot))
