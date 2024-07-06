import discord
from discord.ext import commands
import requests
import sqlite3
import random
import config

# Инициализация бота
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Создание и подключение к базе данных
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Создание таблицы, если её нет
c.execute('''CREATE TABLE IF NOT EXISTS users
             (discord_id TEXT PRIMARY KEY, riot_id TEXT, region TEXT, rank_flex TEXT, wr_flex TEXT, rank_solo TEXT, wr_solo TEXT, role1 TEXT, role2 TEXT, opgg_link TEXT)''')
conn.commit()

# Ваш токен бота
TOKEN = config.discord_bot_token
RIOT_API_KEY = config.riot_api_key
ICON_IDS = ['7', '9', '18', '20', '23']


# class myView(discord.ui.View):
#     @discord.ui.button(label="Button", style=discord.ButtonStyle.red)
#     async def button_callback(self, interaction, button):
#         await interaction.response.edit_message(view=self)

# Функция получения информации из Riot API
def get_account_puuid(name, tag):
    url = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={RIOT_API_KEY}'
    response = requests.get(url)
    return response.json()["puuid"]


def get_summoner_info_by_puuid(region, summoner_puuid):
    url = f'https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{summoner_puuid}?api_key={RIOT_API_KEY}'
    response = requests.get(url)
    return response.json()


def get_ranked_info(region, summoner_id):
    url = f'https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={RIOT_API_KEY}'
    response = requests.get(url)
    return response.json()


@bot.tree.command(name='регистрация', description='Регистрация на турнир')
async def input_command(interaction: discord.Interaction):
    bot.name_data = ''
    bot.primary_role = ''
    bot.secondary_role = ''
    bot.server_data = ''
    bot.account_puuid = ''
    bot.account_name = ''
    bot.account_tag = ''
    bot.account_puuid = ''
    bot.rank_solo = ''
    bot.rank_flex = ''
    bot.winrate_ranked_solo = ''
    bot.winrate_ranked_flex = ''
    options = [
        discord.SelectOption(label="Top", value="top", default=False),
        discord.SelectOption(label="Bot", value="bot", default=False),
        discord.SelectOption(label="Mid", value="mid", default=False),
        discord.SelectOption(label="Sup", value="sup", default=False),
        discord.SelectOption(label="Jng", value="jng", default=False),
        discord.SelectOption(label="Fill", value="fill", default=False)
    ]

    server_options = [
        discord.SelectOption(label="RU", value="ru", default=False),
        discord.SelectOption(label="EUW", value="euw1", default=False)
    ]

    def choose_random_icon(icon_list):
        return random.choice(icon_list)

    random_icon = choose_random_icon(ICON_IDS)

    class TextInputView(discord.ui.View):
        @discord.ui.button(label="Начать", style=discord.ButtonStyle.primary)
        async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = TextInputModal(user_id=interaction.user.id)
            await interaction.response.send_modal(modal)

    class TextInputModal(discord.ui.Modal):
        def __init__(self, user_id):
            super().__init__(title="Форма регистрации на турнир")
            self.user_id = user_id
            self.text_input = discord.ui.TextInput(
                label="Введите ваш RiotID в формате Ник#тег",
                placeholder="Kuzhnya#666"
            )

            self.add_item(self.text_input)

        async def on_submit(self, interaction: discord.Interaction):
            user_text = self.text_input.value
            bot.name_data = user_text  # Store the text data
            bot.account_name, bot.account_tag = bot.name_data.split('#')
            bot.account_puuid = get_account_puuid(bot.account_name, bot.account_tag)
            view = SelectRoleMenu()
            await interaction.response.send_message(f"Введенный RiotId: {user_text}. Теперь выберите основную роль.", ephemeral=True, view=view)

    class SelectRoleMenu(discord.ui.View):
        @discord.ui.select(placeholder="Роли", custom_id="test", options=options, max_values=1)
        async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
            bot.primary_role = select.values[0]
            view = SelectRoleMenu2()
            await interaction.response.send_message(f"Основная роль: {bot.primary_role}. Теперь выберите вторую роль (другую) ",
                                                    ephemeral=True, view=view)

    class SelectRoleMenu2(discord.ui.View):
        @discord.ui.select(placeholder="Роли", custom_id="test", options=options, max_values=1)
        async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
            bot.secondary_role = select.values[0]
            view = SelectServerMenu()
            await interaction.response.send_message(f"Выбрана роль: {bot.secondary_role}. Теперь выберите сервер аккаунта", ephemeral=True, view=view)

    # noinspection PyUnresolvedReferences
    class SelectServerMenu(discord.ui.View):
        @discord.ui.select(placeholder="Select", custom_id="test", options=server_options, max_values=1)
        async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
            bot.server_data = select.values[0]
            view = CheckIconButton()
            await interaction.response.send_message(
                f"Пожалуйста, измените свою иконку на ID {random_icon}, затем нажмите на кнопку", ephemeral=True,
                view=view)

    class CheckIconButton(discord.ui.View):
        @discord.ui.button(label="Готово", style=discord.ButtonStyle.primary)
        async def check_icon_1(self, interaction: discord.Interaction, button: discord.ui.Button):
            try:
                current_icon_id = get_summoner_info_by_puuid(bot.server_data, bot.account_puuid)['profileIconId']
                if str(current_icon_id) == random_icon:
                    opgg_link = f"https://www.op.gg/summoners/{bot.server_data}/{bot.account_name}-{bot.account_tag}"
                    summoner_info = get_summoner_info_by_puuid(bot.server_data, bot.account_puuid)
                    ranked_info = get_ranked_info(bot.server_data, summoner_info['id'])
                    for entry in ranked_info:
                        if entry['queueType'] == 'RANKED_SOLO_5x5':
                            bot.rank_solo = entry['tier'] + " " + entry['rank']
                            bot.winrate_ranked_solo= str(entry['wins']/(entry['losses']+entry['wins'])*100)
                        elif entry['queueType'] == 'RANKED_FLEX_SR':
                            bot.rank_flex = str(entry['tier'] + " " + entry['rank'])
                            bot.winrate_ranked_flex = str(entry['wins'] / (entry['losses'] + entry['wins']) * 100)
                    c.execute(
                        "INSERT INTO users (discord_id, riot_id, region, rank_flex, wr_flex, rank_solo, wr_solo, role1, role2, opgg_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (str(interaction.user.id), bot.name_data, bot.server_data, bot.rank_flex, bot.winrate_ranked_flex, bot.rank_solo, bot.winrate_ranked_solo, bot.primary_role, bot.secondary_role,
                         opgg_link))
                    conn.commit()
                    print('Всё отправлено')
                    await interaction.response.send_message(f"Регистрация завершена", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Ошибка", ephemeral=True)
            except sqlite3.IntegrityError:
                await interaction.response.send_message(f"Вы уже регистрировались", ephemeral=True)

    view = TextInputView()
    await interaction.response.send_message("Нажмите на кнопку для начала регистрации", view=view,
                                            ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}!')

bot.run(TOKEN)


