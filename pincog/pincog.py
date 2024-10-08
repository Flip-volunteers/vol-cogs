import asyncio
import discord
from discord.ext import commands
import discord.ext.commands
from redbot.core import Config, commands, checks
from redbot.core.bot import Red

import discord.ext


class pincog(commands.Cog):
    """A cog to allow non admins to pin messages via a settable role"""

    def __init__(self, bot):
        self.bot = bot

        # see https://docs.discord.red/en/stable/framework_config.html for config storage
        self.config = Config.get_conf(self, identifier=13371590, force_registration=True)
        default_guild = {"pin_role": []}
        self.config.register_global(**default_guild)
        self.config.register_guild(**default_guild)

    async def is_pinner(self, member: discord.Member):
        guild_group = self.config.guild(member.guild)
        pin_role_id = await guild_group.pin_role()
        if pin_role_id is None:
            return False
        for role in member.roles:
            if role.id == pin_role_id:
                return True
        return False


    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def checkpinrole(self, ctx):
        """Show the current role authorized for pinning"""
        data = await self.config.guild(ctx.guild).all()
        if data["pin_role"] == [] or data["pin_role"] == None:
            return await ctx.send("No role set")
        pinner_role = ctx.guild.get_role(data['pin_role'])
        msg = ("Pinrole is: {role}".format(role=pinner_role.mention if pinner_role else ("None")))
        await ctx.maybe_send_embed(msg)
    
    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def setpinrole(self,ctx, pinrole: discord.Role):
        """Set the role allowed to pin messages"""
        guild_group = self.config.guild(ctx.guild)
        await guild_group.pin_role.set(pinrole.id)
        await ctx.send(f"set role to {pinrole.name}")

    @commands.command()
    @commands.guild_only()
    async def pinmsg(self, ctx, message_id):
        """Pin a message by its ID"""
        if not await self.is_pinner(ctx.author):
            return await ctx.send("You are not authorized for pinning.")
        if "discord.com/channels/" in message_id:
            try:
                parts = message_id.split('/')
                message_id = parts[-1]
            except IndexError:
                return await ctx.send("Invalid link")
        # discord message ID's should always be 18 in length
        elif len(message_id) != 18:
            return await ctx.send(f"Got incorrect ID length, check formatting.\n {len(message_id)} {message_id}")
        try:
            message = await ctx.channel.fetch_message(message_id)
            await message.pin()
            await ctx.send(f"message {message_id} pinned")
        except discord.NotFound:
            ctx.send("Message not found.")
        except discord.Forbidden:
            await ctx.send("Missing permissions to pin here.")
        except discord.HTTPException:
            await ctx.send("Improper ID or link, please check the message ID is valid.")
        except Exception as e:
            print(f"error occured: {e}")


    @commands.command()
    @commands.guild_only()
    async def pinroleselfcheck(self,ctx):
        """Test if user using this command is authorized to use pinning"""
        if not await self.is_pinner(ctx.author):
            return await ctx.send("You do not have the role for pinning.")
        await ctx.send("You are authorized for pinning.")