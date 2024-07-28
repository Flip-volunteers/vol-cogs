from redbot.core import commands, modlog, checks
import discord


# Classname should be CamelCase and the same spelling as the folder
class ModlogKillcount(commands.Cog):
    """Aux modlog cog for handling various custom commands"""
 
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.mod_or_permissions(ban_members=True)
    async def killcount(self, ctx):
        """Gets the killcount on the server"""
        moderators_killcount = {}
        for log in await modlog.get_all_cases(ctx.guild, self.bot):
            action_type = log.action_type
            if not log.moderator is None:
                if not log.moderator.name in moderators_killcount:
                    moderators_killcount[log.moderator.name] = {}
                if not action_type in moderators_killcount[log.moderator.name]:
                    moderators_killcount[log.moderator.name][action_type] = 0

                moderators_killcount[log.moderator.name][action_type] += 1

        output_text = ''
        await ctx.send("Killcount stats:")
        for mod in moderators_killcount:
            await ctx.send(f"{mod}: {moderators_killcount[mod].keys()}")
            
