from .MessageMover import MessageMover
import asyncio


async def setup(bot):
    await bot.add_cog(MessageMover(bot))
