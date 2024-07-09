from typing import Optional
import discord
from discord.ext import commands
import requests
import sqlite3
import random
import config
from dataclasses import dataclass, asdict

# Инициализация бота
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
USER_REGISTRATION_DICT = {}

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


@dataclass
class UserInfo:
    name_data: Optional[str] = None
    primary_role: Optional[str] = None
    secondary_role: Optional[str] = None
    server_data: Optional[str] = None
    account_name: Optional[str] = None
    account_tag: Optional[str] = None
    rank_solo: Optional[str] = None
    rank_flex: Optional[str] = None
    winrate_ranked_solo: Optional[str] = None
    winrate_ranked_flex: Optional[str] = None
    account_puuid: Optional[str] = None
    required_icon: Optional[str] = None


USER_INFO_DICT: dict[str, UserInfo] = dict()


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


# Функция для выбора случайной id иконки из словаря
def choose_random_icon():
    random_icon = random.choice(list(ICON_DICT.keys()))
    return random_icon


# Основная команда, реализована через декоратор CommandTree
@bot.tree.command(name='регистрация', description='Регистрация на турнир')
async def input_command(interaction: discord.Interaction):
    # Добавление всех необходимых переменных в функцию
    USER_INFO_DICT[str(interaction.user.id)] = UserInfo()
    labels_values = ["Top", "Bot", "Mid", "Sup", "Jng", "Fill"]

    options = [
        discord.SelectOption(label=label, value=label.lower(), default=False)
        for label in labels_values
    ]

    server_options = [
        discord.SelectOption(label="RU", value="ru", default=False),
        discord.SelectOption(label="EUW", value="euw1", default=False)
    ]

    # Далее идут классы View по сути добавляющие текст, кнопки и менюшки
    class TextInputView(discord.ui.View):
        @discord.ui.button(label="Начать", style=discord.ButtonStyle.primary)
        async def open_form(self, interaction_start: discord.Interaction, button: discord.ui.Button):
            modal = TextInputModal(user_id=interaction_start.user.id)
            await interaction_start.response.send_modal(modal)

    class TextInputModal(discord.ui.Modal):  # Самый п*дорский класс, не трогайте
        def __init__(self, user_id):
            super().__init__(title="Форма регистрации на турнир")
            self.user_id = user_id
            self.text_input = discord.ui.TextInput(
                label="Введите ваш RiotID в формате Ник#тег",
                placeholder="Kuzhnya#666"
            )

            self.add_item(self.text_input)

        async def on_submit(self, interaction_on_submit: discord.Interaction):
            user_text = self.text_input.value
            USER_INFO_DICT[str(interaction_on_submit.user.id)].name_data = user_text
            try:
                USER_INFO_DICT[str(interaction_on_submit.user.id)].account_name, USER_INFO_DICT[str(interaction_on_submit.user.id)].account_tag = USER_INFO_DICT[str(interaction_on_submit.user.id)].name_data.split('#')
                USER_INFO_DICT[str(interaction_on_submit.user.id)].account_puuid = get_account_puuid(USER_INFO_DICT[str(interaction_on_submit.user.id)].account_name, USER_INFO_DICT[str(interaction_on_submit.user.id)].account_tag)
                view = SelectRoleMenu()
                await interaction_on_submit.response.send_message(f"Введенный RiotId: {user_text}. Теперь выберите основную роль:",
                                                                  ephemeral=True, view=view, delete_after=float(20))
            except:
                await interaction_on_submit.response.send_message(
                    f"Неверный формат RiotId. Введите команду /регистрация ещё раз. Пример RiotId: Kuzhnya#666",
                    ephemeral=True, delete_after=float(20))

    class SelectRoleMenu(discord.ui.View):
        @discord.ui.select(placeholder="Роли", custom_id="select_role_1", options=options, max_values=1)
        async def role_select(self, interaction_select_1: discord.Interaction, select: discord.ui.Select):
            USER_INFO_DICT[str(interaction_select_1.user.id)].primary_role = select.values[0]
            view = SelectRoleMenu2()
            await interaction_select_1.response.send_message(
                f"Основная роль: {USER_INFO_DICT[str(interaction_select_1.user.id)].primary_role}. Теперь выберите вторую роль (другую).",
                ephemeral=True, view=view, delete_after=float(20))

    class SelectRoleMenu2(discord.ui.View):
        @discord.ui.select(placeholder="Роли", custom_id="select_role_2", options=options, max_values=1)
        async def role_select(self, interaction_select_2: discord.Interaction, select: discord.ui.Select):
            USER_INFO_DICT[str(interaction_select_2.user.id)].secondary_role = select.values[0]
            view = SelectServerMenu()
            await interaction_select_2.response.send_message(
                f"Выбрана роль: {USER_INFO_DICT[str(interaction_select_2.user.id)].secondary_role}. Теперь выберите сервер аккаунта.", ephemeral=True, view=view, delete_after=float(20))

    # noinspection PyUnresolvedReferences
    class SelectServerMenu(discord.ui.View):
        @discord.ui.select(placeholder="Select", custom_id="select_role_3", options=server_options, max_values=1)
        async def role_select(self, interaction_select_3: discord.Interaction, select: discord.ui.Select):
            USER_INFO_DICT[str(interaction_select_3.user.id)].server_data = select.values[0]
            USER_INFO_DICT[str(interaction_select_3.user.id)].required_icon = choose_random_icon()
            view = CheckIconButton()
            await interaction_select_3.response.send_message(
                f"Сервер {USER_INFO_DICT[str(interaction_select_3.user.id)].server_data}! Пожалуйста, измените свою иконку на {ICON_DICT[USER_INFO_DICT[str(interaction_select_3.user.id)].required_icon]}, затем нажмите на кнопку. У вас две минуты.", ephemeral=True,
                view=view, delete_after=float(120))

    class CheckIconButton(discord.ui.View):
        @discord.ui.button(label="Готово", style=discord.ButtonStyle.primary)
        async def check_icon_1(self, interaction_check_button: discord.Interaction, button: discord.ui.Button):  # Собственно функция проверки иконки, она же функция отправления данных в бд
            try:
                current_icon_id = get_summoner_info_by_puuid(USER_INFO_DICT[str(interaction_check_button.user.id)].server_data, USER_INFO_DICT[str(interaction_check_button.user.id)].account_puuid)['profileIconId']
                if str(current_icon_id) == USER_INFO_DICT[str(interaction_check_button.user.id)].required_icon:  # Если иконка при нажатии кнопки совпадает с требуемой -> True
                    opgg_link = f"https://www.op.gg/summoners/{USER_INFO_DICT[str(interaction_check_button.user.id)].server_data}/{USER_INFO_DICT[str(interaction_check_button.user.id)].account_name}-{USER_INFO_DICT[str(interaction_check_button.user.id)].account_tag}"
                    summoner_info = get_summoner_info_by_puuid(USER_INFO_DICT[str(interaction_check_button.user.id)].server_data, USER_INFO_DICT[str(interaction_check_button.user.id)].account_puuid)
                    ranked_info = get_ranked_info(USER_INFO_DICT[str(interaction_check_button.user.id)].server_data, summoner_info['id'])
                    for entry in ranked_info:  # Обработчик ответа от get_ranked_info. Иногда приходит как словарь, иногда как список словарей, иногда пустой
                        if entry['queueType'] == 'RANKED_SOLO_5x5':
                            USER_INFO_DICT[str(interaction_check_button.user.id)].rank_solo = entry['tier'] + " " + entry['rank']
                            USER_INFO_DICT[str(interaction_check_button.user.id)].winrate_ranked_solo = str(round(entry['wins'] / (entry['losses'] + entry['wins']) * 100, 2)) + "%"
                        elif entry['queueType'] == 'RANKED_FLEX_SR':
                            USER_INFO_DICT[str(interaction_check_button.user.id)].rank_flex = str(entry['tier'] + " " + entry['rank'])
                            USER_INFO_DICT[str(interaction_check_button.user.id)].winrate_ranked_flex = str(round(entry['wins'] / (entry['losses'] + entry['wins']) * 100, 2)) + "%"
                    c.execute(
                        "INSERT INTO users (discord_id, riot_id, region, rank_flex, wr_flex, rank_solo, wr_solo, role1, role2, opgg_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (str(interaction_check_button.user.id), USER_INFO_DICT[str(interaction_check_button.user.id)].name_data, USER_INFO_DICT[str(interaction_check_button.user.id)].server_data, USER_INFO_DICT[str(interaction_check_button.user.id)].rank_flex,
                         USER_INFO_DICT[str(interaction_check_button.user.id)].winrate_ranked_flex,
                         USER_INFO_DICT[str(interaction_check_button.user.id)].rank_solo, USER_INFO_DICT[str(interaction_check_button.user.id)].winrate_ranked_solo, USER_INFO_DICT[str(interaction_check_button.user.id)].primary_role, USER_INFO_DICT[str(interaction_check_button.user.id)].secondary_role, opgg_link))
                    conn.commit()
                    await interaction_check_button.response.send_message(f"Регистрация завершена.", ephemeral=True, delete_after=float(10))
                else:
                    await interaction_check_button.response.send_message(
                        f"Ошибка, неверная иконка. Введите команду /регистрация ещё раз.", ephemeral=True, delete_after=float(20))
            except sqlite3.IntegrityError:  # Эта ошибка выползает если discord_id пользователя в бд уже есть
                await interaction_check_button.response.send_message(f"Вы уже регистрировались.", ephemeral=True, delete_after=float(20))

    start_view = TextInputView()  # Самый первый view, после него выводятся по порядку
    await interaction.response.send_message("Нажмите на кнопку для начала регистрации.", view=start_view, ephemeral=True, delete_after=float(20))


@bot.event  # Этот ивент нужен для подгрузки команды через bot.tree.command
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}!')


bot.run(TOKEN)
