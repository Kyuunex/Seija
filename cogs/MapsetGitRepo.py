import discord
from discord.ext import commands
from modules import permissions


class MapsetGitRepo(commands.Cog):
    """
    [THIS DOES NOT WORK FOR NOW]
    TODO: email peppy and ask to make the BSS not upload anything that starts with .git

    This set of commands will allow you to create a git repository for your mapset
    to make dealing with syncing file changes easier with your Guest Mappers or Collaborators.

    To use this,
    > make sure you have `git` installed
    > make sure you created git credentials on my server with the .create_git_credentials command
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="import_repo", brief="Import a git repository")
    @commands.check(permissions.is_owner)
    async def import_repo(self, ctx):
        git_url = ""

        how_to_import = "To import your mapset folder as a repository, "
        how_to_import += "navigate to your mapset folder, open a terminal/cmd/git bash and type the following:\n"
        how_to_import += "```\n"
        how_to_import += "git init\n"
        how_to_import += "git add *\n"
        how_to_import += "git commit -m \"first commit\"\n"
        how_to_import += f"git remote add origin {git_url}\n"
        how_to_import += "git push -u origin master\n"
        how_to_import += "```\n"
        how_to_import += "After that, type the command `.update_git_permissions`"

        await ctx.send(how_to_import)

    @commands.command(name="create_git_credentials", brief="Create credentials to use on my git server")
    @commands.check(permissions.is_owner)
    async def create_git_credentials(self, ctx):
        # create agit account for that user,
        # username should be their osu_id and the password should be randomly generated and sent via DM

        # check if the user is part of any mapset that has a git repo and allow that newly made account to commit there
        pass

    @commands.command(name="update_git_permissions", brief="Update git permissions for everyone involved in the mapset")
    @commands.check(permissions.is_owner)
    async def create_git_credentials(self, ctx):
        # if the mapset repo exists,
        # cycle through all mapset members
        # and if they have created their git credentials already,
        # make sure they have all the permissions they should
        pass


def setup(bot):
    bot.add_cog(MapsetGitRepo(bot))
