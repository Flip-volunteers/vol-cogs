from .pincog import pincog
import asyncio


async def setup(bot):
    await bot.add_cog(pincog(bot))
