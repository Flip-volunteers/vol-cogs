import discord
from redbot.core import commands, app_commands, Config
from typing import Union

class ChannelSelect(discord.ui.Select):
    def __init__(self, original_message: discord.Message, category: Union[discord.CategoryChannel, getattr(discord, 'Object', object)], member: discord.Member):
        self.original_message = original_message
        self.member = member

        options = []
        channels = category.text_channels if hasattr(category, 'text_channels') else []

        for channel in channels:
            perms = channel.permissions_for(member)
            if perms.view_channel and perms.send_messages:
                options.append(discord.SelectOption(label=f"#{channel.name}", value=str(channel.id)))

        super().__init__(placeholder="Select a channel...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        target_channel = interaction.guild.get_channel(int(self.values[0]))
        if not target_channel.permissions_for(interaction.guild.me).manage_webhooks:
            return await interaction.response.send_message("I need 'Manage Webhooks' in that channel!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        webhook = None
        try:
            # 1. Send notification including the name of the user who moved it
            await target_channel.send(
                f"Hey {self.original_message.author.mention}, your message was moved here from "
                f"{self.original_message.channel.mention} by **{interaction.user.display_name}**."
            )

            # 2. Create temporary Webhook
            webhook = await target_channel.create_webhook(name=f"MoveHook-{self.original_message.id}")

            # 3. Transfer content
            files = [await a.to_file() for a in self.original_message.attachments]
            await webhook.send(
                content=self.original_message.content,
                username=self.original_message.author.display_name,
                avatar_url=self.original_message.author.display_avatar.url,
                embeds=self.original_message.embeds,
                files=files,
                allowed_mentions=discord.AllowedMentions.none()
            )

            # 4. Cleanup original message and selector
            await self.original_message.delete()
            await interaction.edit_original_response(
                content=f"✅ Message by **{self.original_message.author}** moved to {target_channel.mention}.",
                view=None
            )

        except Exception as e:
            await interaction.followup.send(f"Error during move: {e}", ephemeral=True)

        finally:
            # 5. WEBHOOK CLEANUP
            if webhook:
                try:
                    await webhook.delete()
                except discord.HTTPException:
                    pass

class BackButton(discord.ui.Button):
    def __init__(self, original_message, member):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary)
        self.original_message = original_message
        self.member = member

    async def callback(self, interaction: discord.Interaction):
        view = MoveMessageView(self.original_message, self.member)
        await interaction.response.edit_message(content="Step 1: Select a Category", view=view)

class CategorySelect(discord.ui.Select):
    def __init__(self, original_message: discord.Message, member: discord.Member):
        self.original_message = original_message
        self.member = member
        options = []
        sorted_cats = sorted(original_message.guild.categories, key=lambda x: x.position)
        for cat in sorted_cats:
            if any(c.permissions_for(member).view_channel for c in cat.text_channels):
                options.append(discord.SelectOption(label=cat.name, value=str(cat.id)))

        super().__init__(placeholder="Select a Category...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        category_obj = interaction.guild.get_channel(int(self.values[0]))
        view = self.view
        view.clear_items()
        view.add_item(ChannelSelect(self.original_message, category_obj, self.member))
        view.add_item(BackButton(self.original_message, self.member))
        await interaction.response.edit_message(content=f"Pick a channel in **{category_obj.name}**:", view=view)

class MoveMessageView(discord.ui.View):
    def __init__(self, original_message: discord.Message, member: discord.Member):
        super().__init__(timeout=120)
        self.add_item(CategorySelect(original_message, member))

class MessageMover(commands.Cog):
    """Move messages via Context Menu with Role-based access."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=133715902, force_registration=True)
        self.config.register_guild(allowed_roles=[])
        self.ctx_menu = app_commands.ContextMenu(name='Move-Message', callback=self.move_message_callback)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    @commands.group()
    @commands.admin_or_permissions(manage_guild=True)
    async def moveset(self, ctx):
        """Settings for MessageMover."""
        pass

    @moveset.command()
    async def addrole(self, ctx, role: discord.Role):
        """Add a role allowed to use the Move Message context menu."""
        async with self.config.guild(ctx.guild).allowed_roles() as roles:
            if role.id not in roles:
                roles.append(role.id)
                await ctx.send(f"✅ {role.name} can now move messages.")
            else:
                await ctx.send("That role is already on the list.")

    @moveset.command()
    async def remrole(self, ctx, role: discord.Role):
        """Remove a role from the allowed list."""
        async with self.config.guild(ctx.guild).allowed_roles() as roles:
            if role.id in roles:
                roles.remove(role.id)
                await ctx.send(f"❌ {role.name} removed from allowed roles.")
            else:
                await ctx.send("That role wasn't in the list.")

    @moveset.command()
    async def list(self, ctx):
        """List all roles allowed to move messages."""
        roles_ids = await self.config.guild(ctx.guild).allowed_roles()
        if not roles_ids:
            return await ctx.send("No specific roles configured. Only users with `Manage Messages` can use this.")

        role_names = [ctx.guild.get_role(rid).name for rid in roles_ids if ctx.guild.get_role(rid)]
        await ctx.send(f"**Allowed Roles:** {', '.join(role_names)}")

    async def move_message_callback(self, interaction: discord.Interaction, message: discord.Message):
        allowed_roles = await self.config.guild(interaction.guild).allowed_roles()
        user_role_ids = [role.id for role in interaction.user.roles]

        has_role = any(rid in allowed_roles for rid in user_role_ids)
        is_mod = interaction.user.guild_permissions.manage_messages

        if not (is_mod or has_role):
            return await interaction.response.send_message("🛡️ You don't have permission to move messages.", ephemeral=True)

        view = MoveMessageView(message, interaction.user)
        await interaction.response.send_message(content="**Move Message**\nStep 1: Select a Category", view=view, ephemeral=True)