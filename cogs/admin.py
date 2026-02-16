import discord
from discord.ext import commands
from discord import app_commands
import traceback
import datetime

from ext.json_guilds import Guilds
from ext.json_tickets import Tickets


def make_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


def status_line(status: str) -> str:
    if status == "Open":
        return ":green_circle: Open"
    if status == "Paused":
        return ":pause_button: Paused"
    return ":red_circle: Closed"


class OrderView(discord.ui.View):
    def __init__(self, guilds: Guilds, tickets: Tickets, admin_cog):
        super().__init__(timeout=None)
        self.guilds = guilds
        self.tickets = tickets
        self.admin_cog = admin_cog

    @discord.ui.button(label="Start Order", style=discord.ButtonStyle.primary, emoji="🧾", custom_id="tfp:create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.guild is None:
            embed = make_embed("Heads up", "This can only be used in a server.", discord.Color.orange())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        guild_data = await self.guilds.get_guild(interaction.guild.id)
        status = guild_data.get("status", "Closed")

        if status == "Closed":
            embed = make_embed(":no_entry: Store closed", "Orders are not available right now.", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if status == "Paused":
            embed = make_embed(
                "Store paused",
                "Orders are temporarily paused. Press the **Notify Me** button to be alerted when we reopen.",
                discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Limit check
        limit = guild_data.get("ticket_limit", 0)
        today_count = guild_data.get("tickets_today", 0)
        
        # Check for date reset
        today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        if guild_data.get("last_reset") != today_str:
            await self.guilds.reset_daily_tickets(interaction.guild.id, today_str)
            today_count = 0
            
        if limit > 0 and today_count >= limit:
            embed = make_embed(":no_entry: Limit reached", "The daily ticket limit has been reached. Please try again tomorrow.", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        category_id = guild_data.get("category_id")
        category = interaction.guild.get_channel(category_id)
        if category is None or not isinstance(category, discord.CategoryChannel):
            embed = make_embed(
                "Missing category",
                "Order category is missing. Please contact an admin.",
                discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        channel_name = f"order-{interaction.user.name}".lower().replace(" ", "-")
        ticket_channel = await interaction.guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
        )

        await self.tickets.insert_ticket(ticket_channel.id, interaction.user.id)
        await self.guilds.increment_tickets_today(interaction.guild.id)

        # Update panel to reflect new count
        await self._update_parent_panel(interaction.guild.id)

        embed = make_embed(
            ":hamburger: Thanks for opening a ticket!",
            "Please describe your order request below and one of the staff members will get to you as soon as possible.",
            discord.Color.blurple(),
        )
        await ticket_channel.send(embed=embed, view=CloseTicketView(self.tickets))
        embed = make_embed(
            "Ticket created",
            f"Your ticket has been created: {ticket_channel.mention}",
            discord.Color.green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Notify Me", style=discord.ButtonStyle.secondary, emoji="🔔", custom_id="tfp:notify_me")
    async def notify_me(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            guild_data = await self.guilds.get_guild(interaction.guild.id)
        except:
            guild_data = {}
            
        status = guild_data.get("status", "Closed")

        if status == "Open":
            embed = make_embed("Store is open", "Orders are currently open! You can start one now.", discord.Color.green())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        notify_list = guild_data.get("notify", [])
        if interaction.user.id in notify_list:
            await self.guilds.remove_notify(interaction.guild.id, interaction.user.id)
            embed = make_embed(
                "Notifications removed",
                "You have been removed from the notify list. You will no longer receive a DM when we reopen.",
                discord.Color.red(),
            )
        else:
            await self.guilds.add_notify(interaction.guild.id, interaction.user.id)
            embed = make_embed(
                "Notification set",
                "You have been added to the notify list. We will DM you when we reopen.",
                discord.Color.orange(),
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _update_parent_panel(self, guild_id: int):
        guild_data = await self.guilds.get_guild(guild_id)
        await self.admin_cog._update_order_panel(guild_id, guild_data.get("status", "Closed"))


class CloseTicketView(discord.ui.View):
    def __init__(self, tickets: Tickets):
        super().__init__(timeout=None)
        self.tickets = tickets

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="tfp:close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel is None:
            return

        channel = interaction.channel
        await self.tickets.remove_ticket(channel.id)
        embed = make_embed("Closing ticket", "This channel will be deleted shortly.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await channel.delete()

class Admin(commands.Cog):

    def __init__(self, bot : commands.Bot) -> None:
        self.bot = bot
        self.guild = Guilds()
        self.tickets = Tickets()
        self.order_view = OrderView(self.guild, self.tickets, self)
        self.close_view = CloseTicketView(self.tickets)

    async def cog_load(self) -> None:
        self.bot.add_view(self.order_view)
        self.bot.add_view(self.close_view)

    async def cog_unload(self) -> None:
        self.bot.remove_view(self.order_view)
        self.bot.remove_view(self.close_view)

    @app_commands.command(name="setup", description="[ADMIN] Sets up the server with the bot")
    async def setup_bot(self, interaction : discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            if not interaction.user.guild_permissions.administrator:
                embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            if await self.guild.does_guild_exist(interaction.guild.id):
                embed = make_embed(":no_entry: Error!", "This server is already setup!", discord.Color.red())
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create category first
            category = await interaction.guild.create_category("🛒〡Orders")
            # Set basic permissions for category
            await category.set_permissions(interaction.guild.default_role, view_channel=False)
            await category.set_permissions(interaction.guild.me, view_channel=True, send_messages=True)

            order_channel = await interaction.guild.create_text_channel("🛒〡order-here", category=category)
            # Allow everyone to see the order channel
            await order_channel.set_permissions(interaction.guild.default_role, view_channel=True, send_messages=False)

            embed = await self._order_panel_embed(interaction.guild.id, "Closed")
            message = await order_channel.send(embed=embed, view=OrderView(self.guild, self.tickets, self))

            await self.guild.insert_guild(interaction.guild.id, order_channel.id, message.id, category.id)
            # Re-update the panel to handle button visibility if it was open (though it starts Closed)
            await self._update_order_panel(interaction.guild.id, "Closed")
            embed = make_embed("Setup complete", "Orders category, channel and button are ready.", discord.Color.green())
            await interaction.followup.send(embed=embed, ephemeral=True)
        except:
            traceback.print_exc()

    @app_commands.command(name="limit", description="[ADMIN] Set daily ticket limit (0 for unlimited)")
    @app_commands.describe(amount="The maximum number of tickets allowed per day (0 for no limit)")
    async def set_limit(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if amount < 0:
            embed = make_embed(":no_entry: Error!", "Limit cannot be negative!", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await self.guild.set_ticket_limit(interaction.guild.id, amount)
        guild_data = await self.guild.get_guild(interaction.guild.id)
        await self._update_order_panel(interaction.guild.id, guild_data.get("status", "Closed"))
        
        limit_text = f"{amount}" if amount > 0 else "None (Unlimited)"
        embed = make_embed("Limit updated", f"Daily ticket limit set to: **{limit_text}**", discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="settoday", description="[ADMIN] Set current ticket count for today")
    @app_commands.describe(amount="The current number of tickets created today")
    async def set_today_count(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if amount < 0:
            embed = make_embed(":no_entry: Error!", "Count cannot be negative!", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await self.guild.set_tickets_today(interaction.guild.id, amount)
        guild_data = await self.guild.get_guild(interaction.guild.id)
        await self._update_order_panel(interaction.guild.id, guild_data.get("status", "Closed"))
        
        embed = make_embed("Count updated", f"Tickets created today set to: **{amount}**", discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Displays the available command list")
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        description = (
            "Here are all the available commands:\n\n"
            "**Admin Commands**\n"
            "`/setup` – Setup the server with the initial ticket panel\n"
            "`/limit <amount>` – Set daily ticket limit (0 for unlimited)\n"
            "`/settoday <amount>` – Set current ticket count for today\n"
            "`/pause` – Pause new order creation\n"
            "`/open` – Open order creation and notify users\n"
            "`/unpause` – Re-open order creation and notify users\n"
            "`/close` – Completely close order creation\n"
            "`/help` – Displays this help message"
        )
        embed = discord.Embed(description=description, color=discord.Color.blurple())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="pause", description="[ADMIN] Pause new order creation")
    async def pause_store(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await self.guild.update_status(interaction.guild.id, "Paused")
        await self._update_order_panel(interaction.guild.id, "Paused")
        embed = make_embed("Store paused", "Users will be added to the notify list.", discord.Color.orange())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="open", description="[ADMIN] Open order creation and notify users")
    async def open_store(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await self._open_and_notify(interaction)

    @app_commands.command(name="unpause", description="[ADMIN] Re-open order creation and notify users")
    async def unpause_store(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await self._open_and_notify(interaction)

    @app_commands.command(name="close", description="[ADMIN] Completely close order creation")
    async def close_store(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await self.guild.update_status(interaction.guild.id, "Closed")
        await self._update_order_panel(interaction.guild.id, "Closed")
        embed = make_embed("Store closed", "Orders are now closed.", discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _open_and_notify(self, interaction: discord.Interaction):
        guild_data = await self.guild.get_guild(interaction.guild.id)
        notify_list = guild_data.get("notify", [])

        await self.guild.update_status(interaction.guild.id, "Open")
        await self._update_order_panel(interaction.guild.id, "Open")
        embed = make_embed("Store open", "The store can now accept orders!", discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)

        for user_id in notify_list:
            user = interaction.guild.get_member(user_id)
            if user is None:
                continue
            try:
                dm_embed = make_embed(
                    ":shopping_cart: We are open again",
                    "You can place your order now in the server.",
                    discord.Color.green(),
                )
                await user.send(embed=dm_embed)
            except:
                traceback.print_exc()

        await self.guild.clear_notifies(interaction.guild.id)

    async def _order_panel_embed(self, guild_id: int, status: str) -> discord.Embed:
        try:
            guild_data = await self.guild.get_guild(guild_id)
        except:
            guild_data = {}
        
        limit = guild_data.get("ticket_limit", 0)
        today_count = guild_data.get("tickets_today", 0)
        
        # Check for date reset
        today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        if guild_data and guild_data.get("last_reset") != today_str:
            # Only reset if the guild actually exists in the DB to avoid setup errors
            if await self.guild.does_guild_exist(guild_id):
                await self.guild.reset_daily_tickets(guild_id, today_str)
                today_count = 0
            else:
                today_count = 0

        limit_info = ""
        if limit > 0:
            remaining = max(0, limit - today_count)
            limit_info = f"\n\n**Tickets Remaining:** {remaining}:{limit}"

        description = (
            "Tap the button below to open a private order ticket.\n"
            "Subtotal Requirement: $20-$25\nFOR BEST PRICE: $20-21 subtotal\n\n"
            f"**Store status:** {status_line(status)}"
            f"{limit_info}"
        )
        return make_embed(":shopping_cart: Discounted UE DELIVERY orders!", description, discord.Color.blurple())

    async def _update_order_panel(self, guild_id: int, status: str) -> None:
        try:
            guild_data = await self.guild.get_guild(guild_id)
            channel_id = guild_data.get("order_channel")
            message_id = guild_data.get("order_message")
            if channel_id is None or message_id is None:
                return

            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)
            if channel is None:
                return

            message = await channel.fetch_message(message_id)
            embed = await self._order_panel_embed(guild_id, status)
            
            view = OrderView(self.guild, self.tickets, self)
            if status == "Open":
                view.remove_item(view.notify_me)
            
            await message.edit(embed=embed, view=view)
        except:
            traceback.print_exc()
    

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
    print("Admin cog loaded\n---")