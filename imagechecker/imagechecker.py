import asyncio
import discord
import imagehash
import io
from datetime import timedelta
from PIL import Image
from redbot.core import Config
from redbot.core import commands, modlog, checks
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.chat_formatting import humanize_timedelta
from red_commons.logging import getLogger
from typing import Literal

logger = getLogger("red.volCogs.imagechecker")

class imagechecker(commands.Cog):
    """A cog to filter images against hashes of spam images using native timeouts."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=14371590, force_registration=True)
        default_guild = {
            "modlog_channel": None,
            "punish_action": "timeout",
            "punish_duration": 600,
            "image_hashes": []
        }
        self.config.register_guild(**default_guild)

    # --- SETTINGS & CHECK COMMANDS ---

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def showhashes(self, ctx):
        """Show currently stored image hashes"""
        hashes = await self.config.guild(ctx.guild).image_hashes()
        if not hashes:
            return await ctx.send("No values stored.")
        output = "\n".join(str(h) for h in hashes)
        for page in pagify(output):
            await ctx.send(box(page, lang="text"))

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def hashcheckimages(self, ctx):
        """Check hashes of images uploaded and displays them (without adding them)"""
        if not ctx.message.attachments:
            return await ctx.send("Please upload at least one image.")
        results = []
        for attachment in ctx.message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                try:
                    image_bytes = await attachment.read()
                    with Image.open(io.BytesIO(image_bytes)) as img:
                        img_hash = str(imagehash.phash(img))
                        results.append(f"{attachment.filename}: {img_hash}")
                except Exception as e:
                    results.append(f"{attachment.filename}: Error processing image.")
            else:
                results.append(f"{attachment.filename}: Skipped (unsupported format).")
        await ctx.send(box("\n".join(results), lang="yaml"))

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def checkmodlogchannel(self, ctx):
        """Check current set channel for modlog messages"""
        channel_id = await self.config.guild(ctx.guild).modlog_channel()
        if not channel_id:
            return await ctx.send("No channel set.")
        modlogchan = ctx.guild.get_channel(channel_id)
        if modlogchan:
            await ctx.send(f"Modlog channel is currently {modlogchan.mention}")
        else:
            await ctx.send("The configured modlog channel no longer exists.")

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def setmodlogchannel(self, ctx, channel: discord.TextChannel):
        """Set the channel where detection logs will be sent"""
        await self.config.guild(ctx.guild).modlog_channel.set(channel.id)
        await ctx.send(f"Modlog channel has been set to {channel.mention}")

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def setpunish(self, ctx, action: Literal["ban", "timeout"], duration: commands.parse_timedelta = None):
        """Set the punishment on detection (e.g., !setpunish timeout 1h)"""
        await self.config.guild(ctx.guild).punish_action.set(action)
        seconds = int(duration.total_seconds()) if duration else 0
        await self.config.guild(ctx.guild).punish_duration.set(seconds)
        time_msg = f"for {duration}" if duration else "permanently"
        await ctx.send(f"Punishment set to **{action}** {time_msg}.")

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def checkpunish(self, ctx):
        """Show the current punishment settings."""
        data = await self.config.guild(ctx.guild).all()
        action = data.get("punish_action")
        seconds = data.get("punish_duration", 0)
        duration_str = humanize_timedelta(timedelta=timedelta(seconds=seconds)) if seconds > 0 else "Permanent"
        await ctx.send(f"Current setting: **{action}** | Duration: **{duration_str}**")

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def addimages(self, ctx):
        """Add images to the blocklist."""
        if not ctx.message.attachments:
            return await ctx.send("Please upload at least one image.")

        processing_log = []
        stored_hashes = await self.config.guild(ctx.guild).image_hashes()
        blacklisted_objects = [imagehash.hex_to_hash(h) for h in stored_hashes]

        for attachment in ctx.message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                try:
                    image_bytes = await attachment.read()
                    with Image.open(io.BytesIO(image_bytes)) as img:
                        new_hash = imagehash.phash(img)

                    if any((new_hash - bl_hash) <= 8 for bl_hash in blacklisted_objects):
                        processing_log.append(f"SKIPPED | {attachment.filename} (Duplicate)")
                    else:
                        async with self.config.guild(ctx.guild).image_hashes() as hashes:
                            hashes.append(str(new_hash))
                        blacklisted_objects.append(new_hash)
                        processing_log.append(f"ADDED   | {attachment.filename}")
                except Exception:
                    processing_log.append(f"ERROR   | {attachment.filename}")
            else:
                processing_log.append(f"IGNORED | {attachment.filename}")

        await ctx.send(box("\n".join(processing_log), lang="ini"))

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def hashremove(self, ctx, hash_to_remove: str):
        """Remove a specific image hash from the blocklist."""
        async with self.config.guild(ctx.guild).image_hashes() as hashes:
            if hash_to_remove in hashes:
                hashes.remove(hash_to_remove)
                await ctx.send(f"Successfully removed hash `{hash_to_remove}`.")
            else:
                await ctx.send("Hash not found.")

    # --- DETECTION LOGIC ---

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot or not message.attachments:
            return

        if message.channel.permissions_for(message.author).manage_messages or await self.bot.is_mod(message.author):
            return

        stored_hashes = await self.config.guild(message.guild).image_hashes()
        if not stored_hashes:
            return

        blacklisted_objects = [imagehash.hex_to_hash(h) for h in stored_hashes]

        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                try:
                    image_bytes = await attachment.read()
                    with Image.open(io.BytesIO(image_bytes)) as img:
                        incoming_hash = imagehash.phash(img)

                    for bl_hash in blacklisted_objects:
                        if (incoming_hash - bl_hash) <= 8:
                            await self.handle_violation(message, str(bl_hash), attachment, image_bytes)
                            return
                except Exception as e:
                    logger.debug(f"Scan error: {e}")

    async def handle_violation(self, message, matched_hash, attachment, image_bytes):
        guild = message.guild
        user = message.author
        fname = attachment.filename
        content = message.content or "[No Text]"
        timestamp = f"<t:{int(message.created_at.timestamp())}:F>"

        try:
            await message.delete()
        except discord.Forbidden:
            pass

        await message.channel.send(
            f"⚠️ {user.mention}, your message was removed for matching known spam images.",
            delete_after=15
        )

        action = await self.config.guild(guild).punish_action()
        seconds = await self.config.guild(guild).punish_duration()
        reason = f"Blacklisted image: {fname} (Match: {matched_hash})"
        punish_str = "None (Cleanup Only)"

        try:
            if action == "ban" and guild.me.guild_permissions.ban_members:
                await guild.ban(user, reason=reason, delete_message_seconds=7200)
                await modlog.create_case(self.bot, guild, message.created_at, "ban", user, guild.me, reason)
                punish_str = "🔨 Ban (Permanent)"

            elif action == "timeout" and guild.me.guild_permissions.moderate_members:
                dur = timedelta(seconds=seconds) if 0 < seconds <= 2419200 else timedelta(days=28)
                await user.timeout(dur, reason=reason)
                try:
                    await modlog.create_case(self.bot, guild, message.created_at, "mtimeout", user, guild.me, reason, dur)
                except:
                    pass
                punish_str = f"⏳ Timeout ({humanize_timedelta(timedelta=dur)})"
            else:
                punish_str = f"⚠️ Attempted {action} (Missing Permissions)"
        except Exception as e:
            logger.error(f"Enforcement failed: {e}")
            punish_str = f"❌ Error applying {action}"

        await self.log_to_modlog(guild, user, content, timestamp, matched_hash, fname, image_bytes, punish_str)

    async def log_to_modlog(self, guild, user, text, time, match_hash, fname, image_bytes, punish_str):
        chan_id = await self.config.guild(guild).modlog_channel()
        channel = guild.get_channel(chan_id)
        if not channel:
            return

        embed = discord.Embed(
            title="🚫 Blacklisted Image Detected",
            color=discord.Color.red(),
            description=f"**User:** {user.mention} ({user.id})\n**Time:** {time}\n"
        )
        embed.add_field(name="Action Applied:", value=f"**{punish_str}**", inline=False)
        embed.add_field(name="User Message:", value=text, inline=False)
        embed.add_field(name="Detected File Name:", value=f"`{fname}`", inline=True)
        embed.add_field(name="Matched Hash:", value=f"`{match_hash}`", inline=True)
        embed.add_field(name="First Detected Image:", value=" ", inline=False)

        file = discord.File(io.BytesIO(image_bytes), filename=f"MATCH_{fname}")
        embed.set_image(url=f"attachment://MATCH_{fname}")
        await channel.send(embed=embed, file=file)