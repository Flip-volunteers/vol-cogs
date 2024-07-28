# This init is required for each cog.
# Import your main class from the cog's folder.
from .modlogkillcount import ModlogKillcount
import asyncio


async def setup(bot):
    # Add the cog to the bot.
    await bot.add_cog(ModlogKillcount(bot))
