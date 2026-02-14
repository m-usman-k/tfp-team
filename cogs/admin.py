import discord
from discord.ext import commands
from discord import app_commands
import traceback

from ext.guild import Guilds
from ext.tickets import Tickets

ORDER_CATEGORY_ID = 1470838111964758161


def make_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


def status_line(status: str) -> str:
    if status == "Open":
        return ":green_circle: Open"
    if status == "Paused":
        return ":pause_button: Paused"
    return ":red_circle: Closed"


class OrderView(discord.ui.View):
    def __init__(self, guilds: Guilds, tickets: Tickets):
        super().__init__(timeout=None)
        self.guilds = guilds
        self.tickets = tickets

    @discord.ui.button(label="Start Order", style=discord.ButtonStyle.primary, emoji="🧾", custom_id="tfp:create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild is None:
            embed = make_embed("Heads up", "This can only be used in a server.", discord.Color.orange())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild_data = await self.guilds.get_guild(interaction.guild.id)
        status = guild_data.get("status", "Closed")

        if status == "Closed":
            embed = make_embed(":no_entry: Store closed", "Orders are not available right now.", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if status == "Paused":
            await self.guilds.add_notify(interaction.guild.id, interaction.user.id)
            embed = make_embed(
                "Store paused",
                "You have been added to the notify list. We will DM you when we reopen.",
                discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        category = interaction.guild.get_channel(ORDER_CATEGORY_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            embed = make_embed(
                "Missing category",
                "Order category is missing. Please contact an admin.",
                discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
        await interaction.response.send_message(embed=embed, ephemeral=True)


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
        self.order_view = OrderView(self.guild, self.tickets)
        self.close_view = CloseTicketView(self.tickets)

    async def cog_load(self) -> None:
        self.bot.add_view(self.order_view)
        self.bot.add_view(self.close_view)

    async def cog_unload(self) -> None:
        self.bot.remove_view(self.order_view)
        self.bot.remove_view(self.close_view)

    @app_commands.command(name="setup", description="[ADMIN] Sets up the server with the bot")
    async def setup_bot(self, interaction : discord.Interaction):
        try:
            if not interaction.user.guild_permissions.administrator:
                embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if await self.guild.does_guild_exist(interaction.guild.id):
                embed = make_embed(":no_entry: Error!", "This server is already setup!", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            order_channel = await interaction.guild.create_text_channel("🛒〡order-here")

            embed = self._order_panel_embed("Closed")
            message = await order_channel.send(embed=embed, view=OrderView(self.guild, self.tickets))

            await self.guild.insert_guild(interaction.guild.id, order_channel.id, message.id)
            embed = make_embed("Setup complete", "Order channel and button are ready.", discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            traceback.print_exc()

    @app_commands.command(name="pause", description="[ADMIN] Pause order creation")
    async def pause_store(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.guild.update_status(interaction.guild.id, "Paused")
        await self._update_order_panel(interaction.guild.id, "Paused")
        embed = make_embed("Store paused", "Users will be added to the notify list.", discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="open", description="[ADMIN] Open order creation and notify users")
    async def open_store(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self._open_and_notify(interaction)

    @app_commands.command(name="unpause", description="[ADMIN] Re-open order creation and notify users")
    async def unpause_store(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self._open_and_notify(interaction)

    @app_commands.command(name="close", description="[ADMIN] Close order creation")
    async def close_store(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            embed = make_embed(":no_entry: Error!", "You need to be an administrator to run this command!", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await self.guild.update_status(interaction.guild.id, "Closed")
        await self._update_order_panel(interaction.guild.id, "Closed")
        embed = make_embed("Store closed", "Orders are now closed.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _open_and_notify(self, interaction: discord.Interaction):
        guild_data = await self.guild.get_guild(interaction.guild.id)
        notify_list = guild_data.get("notify", [])

        await self.guild.update_status(interaction.guild.id, "Open")
        await self._update_order_panel(interaction.guild.id, "Open")
        embed = make_embed("Store open", "The store can now accept orders!", discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

    def _order_panel_embed(self, status: str) -> discord.Embed:
        description = (
            "Tap the button below to open a private order ticket.\n"
            "Subtotal Requirement: $20-$25\nFOR BEST PRICE: $20-21 subtotal\n\n"
            f"**Store status:** {status_line(status)}"
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
                return

            message = await channel.fetch_message(message_id)
            embed = self._order_panel_embed(status)
            await message.edit(embed=embed)
        except:
            traceback.print_exc()
    

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
    print("Admin cog loaded\n---")