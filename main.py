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

# Токены
TOKEN = config.discord_bot_token
RIOT_API_KEY = config.riot_api_key

# Словарь с иконками
ICON_DICT = {'7': 'Розу', '9': 'Два Меча', '18': 'Зелье', '20': 'Пирамиды', '23': 'Росток'}

# Функция для получения puuid аккаунта Riot
def get_account_puuid(name, tag):
    url = f'https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={RIOT_API_KEY}'
    response = requests.get(url)
    return response.json()["puuid"]


# Функция для получения данных об аккаунте Лиги Легенд
def get_summoner_info_by_puuid(region, summoner_puuid):
    url = f'https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{summoner_puuid}?api_key={RIOT_API_KEY}'
    response = requests.get(url)
    return response.json()


# Функция для получения данных о рейтинге пользователя в Лиге Легенд
def get_ranked_info(region, summoner_id):
    url = f'https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={RIOT_API_KEY}'
    response = requests.get(url)
    return response.json()


# Основная команда, реализована через декоратор CommandTree
@bot.tree.command(name='регистрация', description='Регистрация на турнир')
async def input_command(interaction: discord.Interaction):
    # Добавление всех необходимых переменных в функцию
    attributes = [
        'name_data', 'primary_role', 'secondary_role', 'server_data', 'account_puuid', 'account_name',
        'account_tag', 'rank_solo', 'rank_flex', 'winrate_ranked_solo', 'winrate_ranked_flex'
    ]

    for attr in attributes:
        setattr(bot, attr, '')
    labels_values = ["Top", "Bot", "Mid", "Sup", "Jng", "Fill"]

    options = [
        discord.SelectOption(label=label, value=label.lower(), default=False)
        for label in labels_values
    ]

    server_options = [
        discord.SelectOption(label="RU", value="ru", default=False),
        discord.SelectOption(label="EUW", value="euw1", default=False)
    ]

    # Функция для выбора случайной id иконки из словаря
    random_icon = random.choice(list(ICON_DICT.keys()))

    # Далее идут классы View по сути добавляющие текст, кнопки и менюшки
    class TextInputView(discord.ui.View):
        @discord.ui.button(label="Начать", style=discord.ButtonStyle.primary)
        async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = TextInputModal(user_id=interaction.user.id)
            await interaction.response.send_modal(modal)

    class TextInputModal(discord.ui.Modal): # Самый п*дорский класс, не трогайте
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
            bot.name_data = user_text
            try:
                bot.account_name, bot.account_tag = bot.name_data.split('#')
                bot.account_puuid = get_account_puuid(bot.account_name, bot.account_tag)
                view = SelectRoleMenu()
                await interaction.response.send_message(f"Введенный RiotId: {user_text}. Теперь выберите основную роль:",
                                                        ephemeral=True, view=view, delete_after=float(20))
            except ValueError:
                await interaction.response.send_message(
                    f"Неверный формат RiotId. Введите команду /регистрация ещё раз. Пример RiotId: Kuzhnya#666",
                    ephemeral=True, delete_after=float(10))

    class SelectRoleMenu(discord.ui.View):
        @discord.ui.select(placeholder="Роли", custom_id="test", options=options, max_values=1)
        async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
            bot.primary_role = select.values[0]
            view = SelectRoleMenu2()
            await interaction.response.send_message(
                f"Основная роль: {bot.primary_role}. Теперь выберите вторую роль (другую).",
                ephemeral=True, view=view, delete_after=float(20))

    class SelectRoleMenu2(discord.ui.View):
        @discord.ui.select(placeholder="Роли", custom_id="test", options=options, max_values=1)
        async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
            bot.secondary_role = select.values[0]
            view = SelectServerMenu()
            await interaction.response.send_message(
                f"Выбрана роль: {bot.secondary_role}. Теперь выберите сервер аккаунта.", ephemeral=True, view=view, delete_after=float(20))

    # noinspection PyUnresolvedReferences
    class SelectServerMenu(discord.ui.View):
        @discord.ui.select(placeholder="Select", custom_id="test", options=server_options, max_values=1)
        async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
            bot.server_data = select.values[0]
            view = CheckIconButton()
            await interaction.response.send_message(
                f"Сервер {bot.server_data}! Пожалуйста, измените свою иконку на {ICON_DICT[random_icon]}, затем нажмите на кнопку. У вас две минуты.", ephemeral=True,
                view=view, delete_after=float(120))

    class CheckIconButton(discord.ui.View):
        @discord.ui.button(label="Готово", style=discord.ButtonStyle.primary)
        async def check_icon_1(self, interaction: discord.Interaction, button: discord.ui.Button):  # Собственно функция проверки иконки, она же функция отправления данных в бд
            try:
                current_icon_id = get_summoner_info_by_puuid(bot.server_data, bot.account_puuid)['profileIconId']
                if str(current_icon_id) == random_icon:  # Если иконка при нажатии кнопки совпадает с требуемой -> True
                    opgg_link = f"https://www.op.gg/summoners/{bot.server_data}/{bot.account_name}-{bot.account_tag}"
                    summoner_info = get_summoner_info_by_puuid(bot.server_data, bot.account_puuid)
                    ranked_info = get_ranked_info(bot.server_data, summoner_info['id'])
                    for entry in ranked_info:  # Обработчик ответа от get_ranked_info. Иногда приходит как словарь, иногда как список словарей, иногда пустой
                        if entry['queueType'] == 'RANKED_SOLO_5x5':
                            bot.rank_solo = entry['tier'] + " " + entry['rank']
                            bot.winrate_ranked_solo = str(round(entry['wins'] / (entry['losses'] + entry['wins']) * 100, 2)) + "%"
                        elif entry['queueType'] == 'RANKED_FLEX_SR':
                            bot.rank_flex = str(entry['tier'] + " " + entry['rank'])
                            bot.winrate_ranked_flex = str(round(entry['wins'] / (entry['losses'] + entry['wins']) * 100, 2)) + "%"
                    c.execute(
                        "INSERT INTO users (discord_id, riot_id, region, rank_flex, wr_flex, rank_solo, wr_solo, role1, role2, opgg_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (str(interaction.user.id), bot.name_data, bot.server_data, bot.rank_flex,
                         bot.winrate_ranked_flex,
                         bot.rank_solo, bot.winrate_ranked_solo, bot.primary_role, bot.secondary_role, opgg_link))
                    conn.commit()
                    await interaction.response.send_message(f"Регистрация завершена.", ephemeral=True, delete_after=float(10))
                else:
                    await interaction.response.send_message(
                        f"Ошибка, неверная иконка. Введите команду /регистрация ещё раз.", ephemeral=True, delete_after=float(20))
            except sqlite3.IntegrityError:  # Эта ошибка выползает если discord_id пользователя в бд уже есть
                await interaction.response.send_message(f"Вы уже регистрировались.", ephemeral=True, delete_after=float(10))

    view = TextInputView()  # Самый первый view, после него выводятся по порядку
    await interaction.response.send_message("Нажмите на кнопку для начала регистрации.", view=view, ephemeral=True, delete_after=float(10))


@bot.event  # Этот ивент нужен для подгрузки команды через bot.tree.command
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}!')


bot.run(TOKEN)
