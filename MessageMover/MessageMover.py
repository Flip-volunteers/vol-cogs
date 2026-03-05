import discord
from redbot.core import commands, app_commands, Config
from typing import Union

class CustomReasonModal(discord.ui.Modal, title="Move Message: Custom Reason"):
    reason_input = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter the reason for moving this message...",
        min_length=5,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, original_message, target_channel, member):
        super().__init__()
        self.original_message = original_message
        self.target_channel = target_channel
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        reason_text = self.reason_input.value
        await interaction.response.defer(ephemeral=True)
        await execute_move(interaction, self.original_message, self.target_channel, "Custom", reason_text)

async def execute_move(interaction, original_message, target_channel, label, description):
    webhook = None
    try:
        # 1. Notification
        await target_channel.send(
            f"Hey {original_message.author.mention}, your message was moved here from "
            f"{original_message.channel.mention} by **{interaction.user.display_name}**.\n"
            f"**Reason:** {label} — *{description}*"
        )

        # 2. Webhook Setup
        webhook = await target_channel.create_webhook(name=f"MoveHook-{original_message.id}")

        # 3. Transfer
        files = [await a.to_file() for a in original_message.attachments]
        await webhook.send(
            content=original_message.content,
            username=original_message.author.display_name,
            avatar_url=original_message.author.display_avatar.url,
            embeds=original_message.embeds,
            files=files,
            allowed_mentions=discord.AllowedMentions.none()
        )

        # 4. Cleanup
        await original_message.delete()
        await interaction.edit_original_response(
            content=f"✅ Message moved to {target_channel.mention} for reason: **{label}**.",
            view=None
        )
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)
    finally:
        if webhook:
            try: await webhook.delete()
            except: pass

class ReasonSelect(discord.ui.Select):
    def __init__(self, original_message, target_channel, member):
        self.original_message = original_message
        self.target_channel = target_channel
        self.member = member

        reasons = [
            discord.SelectOption(label="Off-topic", description="Message was off topic in the original channel"),
            discord.SelectOption(label="Specialized channel", description="There is a better-suited channel for this topic."),
            discord.SelectOption(label="Delivery talk", description="This message contains delivery-talk channel content"),
            discord.SelectOption(label="Custom Reason", description="Type a specific reason in a popup...", emoji="📝"),
        ]
        super().__init__(placeholder="Select a reason for the move...", options=reasons)

    async def callback(self, interaction: discord.Interaction):
        selected_label = self.values[0]

        if selected_label == "Custom Reason":
            await interaction.response.send_modal(CustomReasonModal(self.original_message, self.target_channel, self.member))
        else:
            selected_option = next(o for o in self.options if o.label == selected_label)
            await interaction.response.defer(ephemeral=True)
            await execute_move(interaction, self.original_message, self.target_channel, selected_label, selected_option.description)

class ChannelSelect(discord.ui.Select):
    def __init__(self, original_message, category, member):
        self.original_message = original_message
        self.member = member
        options = [discord.SelectOption(label=f"#{c.name}", value=str(c.id))
                   for c in category.text_channels if c.permissions_for(member).send_messages][:25]
        super().__init__(placeholder="Select a channel...", options=options)

    async def callback(self, interaction: discord.Interaction):
        target_channel = interaction.guild.get_channel(int(self.values[0]))
        if not target_channel.permissions_for(interaction.guild.me).manage_webhooks:
            return await interaction.response.send_message("I need 'Manage Webhooks' there!", ephemeral=True)

        view = self.view
        view.clear_items()
        view.add_item(ReasonSelect(self.original_message, target_channel, self.member))
        await interaction.response.edit_message(content=f"Final Step: Why are you moving this to {target_channel.mention}?", view=view)

class CategorySelect(discord.ui.Select):
    def __init__(self, original_message, member):
        self.original_message = original_message
        self.member = member
        options = [discord.SelectOption(label=cat.name, value=str(cat.id))
                   for cat in sorted(original_message.guild.categories, key=lambda x: x.position)
                   if any(c.permissions_for(member).view_channel for c in cat.text_channels)][:25]
        super().__init__(placeholder="Select a Category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        category_obj = interaction.guild.get_channel(int(self.values[0]))
        view = self.view
        view.clear_items()
        view.add_item(ChannelSelect(self.original_message, category_obj, self.member))
        await interaction.response.edit_message(content=f"Pick a channel in **{category_obj.name}**:", view=view)

class MoveMessageView(discord.ui.View):
    def __init__(self, original_message, member):
        super().__init__(timeout=120)
        self.add_item(CategorySelect(original_message, member))

class MessageMover(commands.Cog):
    """Move messages with a context menu, reasons, and Modals."""
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=133715902, force_registration=True)
        self.config.register_guild(allowed_roles=[])
        self.ctx_menu = app_commands.ContextMenu(name='Move-Message', callback=self.move_message_callback)
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def move_message_callback(self, interaction: discord.Interaction, message: discord.Message):
        allowed_roles = await self.config.guild(interaction.guild).allowed_roles()
        if not (interaction.user.guild_permissions.manage_messages or any(r.id in allowed_roles for r in interaction.user.roles)):
            return await interaction.response.send_message("🛡️ Permission denied.", ephemeral=True)

        view = MoveMessageView(message, interaction.user)
        await interaction.response.send_message(content="**Move Message**\nStep 1: Select a Category", view=view, ephemeral=True)
