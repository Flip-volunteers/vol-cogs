from .imagechecker import imagechecker
import asyncio

async def setup(bot):
    await bot.add_cog(imagechecker(bot))
