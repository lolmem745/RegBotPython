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
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

USER_REGISTRATION_DICT = {}

# Создание и подключение к базе данных
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Создание таблиц, если их нет
c.execute('''CREATE TABLE IF NOT EXISTS users
             (discord_id TEXT PRIMARY KEY, riot_id TEXT, region TEXT, rank_flex TEXT, 
             wr_flex TEXT, rank_solo TEXT, wr_solo TEXT, role1 TEXT, role2 TEXT, opgg_link TEXT)''')
conn.commit()
c.execute('''CREATE TABLE IF NOT EXISTS categories
             ("index" INTEGER PRIMARY KEY, Категория TEXT, Чемпионы TEXT)''')
conn.commit()

# Импорт из config.py
TOKEN = config.discord_bot_token
RIOT_API_KEY = config.riot_api_key
role_id = config.role_id  # id роли для которой работает /рандом

# Словарь с иконками
ICON_DICT = {'7': 'Розу', '9': 'Два Меча', '18': 'Зелье', '20': 'Пирамиды', '23': 'Росток'}
CATEGORIES_DICT = {}

c.execute("SELECT Категория, Чемпионы FROM categories")
rows = c.fetchall()

for row in rows:
    category = row[0]
    champions_field = row[1]
    if champions_field:
        champions = champions_field.split('\n')  # Чемпионы разделены переносами строки
    else:
        champions = []
    CATEGORIES_DICT[category] = champions
conn.commit()

labels_values = ["Top", "Bot", "Mid", "Sup", "Jng", "Fill"]

options = [
    discord.SelectOption(label=label, value=label.lower(), default=False)
    for label in labels_values
]

server_options = [
    discord.SelectOption(label="RU", value="ru", default=False),
    discord.SelectOption(label="EUW", value="euw1", default=False)
]

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


UID: dict[str, UserInfo] = dict()  # USER_INFO_DICT


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


def send_data_to_db(ds_user_id):
    opgg_link = f"https://www.op.gg/summoners/{UID[ds_user_id].server_data}/" \
                f"{UID[ds_user_id].account_name}-{UID[ds_user_id].account_tag}"
    summoner_info = get_summoner_info_by_puuid(
        UID[ds_user_id].server_data, UID[ds_user_id].account_puuid)
    ranked_info = get_ranked_info(UID[ds_user_id].server_data, summoner_info['id'])
    for entry in ranked_info:
        if entry['queueType'] == 'RANKED_SOLO_5x5':
            UID[ds_user_id].rank_solo = entry['tier'] + " " + entry['rank']
            UID[ds_user_id].winrate_ranked_solo = str(
                round(entry['wins'] / (entry['losses'] + entry['wins']) * 100, 2)) + "%"
        elif entry['queueType'] == 'RANKED_FLEX_SR':
            UID[ds_user_id].rank_flex = str(entry['tier'] + " " + entry['rank'])
            UID[ds_user_id].winrate_ranked_flex = str(
                round(entry['wins'] / (entry['losses'] + entry['wins']) * 100, 2)) + "%"
    c.execute(
        "INSERT INTO users (discord_id, riot_id, region, rank_flex, wr_flex,"
        " rank_solo, wr_solo, role1, role2, opgg_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ds_user_id, UID[ds_user_id].name_data, UID[ds_user_id].server_data, UID[ds_user_id].rank_flex,
         UID[ds_user_id].winrate_ranked_flex,
         UID[ds_user_id].rank_solo, UID[ds_user_id].winrate_ranked_solo, UID[ds_user_id].primary_role,
         UID[ds_user_id].secondary_role,
         opgg_link))
    conn.commit()


# Команда для вывода рандомной категории, персонажей в ней и реролла
@bot.tree.command(name='рандом', description='Выбор случайной категории')
async def category_randomizer(interaction: discord.Interaction):
    def get_random_category():
        return random.choice(list(CATEGORIES_DICT.keys()))

    # Функция для вывода списка героев по переданному значению ключа
    def get_champions_by_category(champion_category):
        return CATEGORIES_DICT.get(champion_category, [])

    if interaction.guild.get_member(interaction.user.id).get_role(role_id) is not None:
        class RerollButtonView(discord.ui.View):
            @discord.ui.button(label="Реролл", style=discord.ButtonStyle.primary, emoji='🎲')
            async def reroll_button_callback(self, interaction_reroll: discord.Interaction, button: discord.ui.Button):
                previous_rand_category = rand_category
                new_rand_category = get_random_category()
                while new_rand_category == previous_rand_category:
                    new_rand_category = get_random_category()
                champions_text = ', '.join(f'{champ}' for champ in get_champions_by_category(new_rand_category))
                new_view = RerollButtonView()
                await interaction.edit_original_response(content=f'Случайная категория: {new_rand_category}\n\nЧемпионы'
                                                                 f' в этой категории: {champions_text}\n⠀', view=new_view)
                await interaction_reroll.response.defer()

        rand_category = get_random_category()
        text = ', '.join(f'{champ}' for champ in get_champions_by_category(rand_category))
        view = RerollButtonView()
        await interaction.response.send_message(
            f'Случайная категория: {rand_category}\n\n'f'Чемпионы в этой категории: '
            f'{text}\n', view=view, silent=True)
    else:
        await interaction.response.send_message('У вас нет прав на использование этой команды.', ephemeral=True)


# Основная команда, собирает данные от пользователя и заносит в таблицу users в users.db
@bot.tree.command(name='регистрация', description='Регистрация на турнир')
async def input_command(interaction: discord.Interaction):
    UID[str(interaction.user.id)] = UserInfo()

    # Далее идут классы View по сути добавляющие текст, кнопки и менюшки
    class TextInputView(discord.ui.View):
        @discord.ui.button(label="Начать", style=discord.ButtonStyle.primary)
        async def open_form(self, interaction_start: discord.Interaction, button: discord.ui.Button):
            modal = TextInputModal(user_id=interaction_start.user.id)
            await interaction_start.response.send_modal(modal)

    class TextInputModal(discord.ui.Modal):
        def __init__(self, user_id):
            super().__init__(title="Форма регистрации на турнир")
            self.user_id = user_id
            self.text_input = discord.ui.TextInput(label="Введите ваш RiotID в формате Ник#тег", placeholder="Kuzhnya#666")
            self.add_item(self.text_input)

        async def on_submit(self, interaction_on_submit: discord.Interaction):
            ios_id = str(interaction_on_submit.user.id)
            user_text = self.text_input.value
            UID[ios_id].name_data = user_text
            try:
                UID[ios_id].account_name, UID[ios_id].account_tag = UID[ios_id].name_data.split('#')
                UID[ios_id].account_puuid = get_account_puuid(UID[ios_id].account_name, UID[ios_id].account_tag)
                view = SelectRoleMenu()
                await interaction.edit_original_response(
                    content=f"Введенный Riot Id: {user_text}. Теперь выберите основную роль:", view=view)
                await interaction_on_submit.response.defer()
            except ValueError:
                await interaction_on_submit.response.send_message(
                    f"Неверный формат Riot Id. Введите команду /регистрация ещё раз. Пример RiotId: Kuzhnya#666",
                    ephemeral=True, delete_after=float(20))

    class SelectRoleMenu(discord.ui.View):
        @discord.ui.select(placeholder="Роли", custom_id="select_role_1", options=options, max_values=1)
        async def role_select(self, interaction_select_1: discord.Interaction, select: discord.ui.Select):
            is1_id = str(interaction_select_1.user.id)
            UID[is1_id].primary_role = select.values[0]
            view = SelectRoleMenu2()
            await interaction.edit_original_response(
                content=f"Основная роль: {UID[is1_id].primary_role}. Теперь выберите вторую роль (другую).", view=view)
            await interaction_select_1.response.defer()

    class SelectRoleMenu2(discord.ui.View):
        @discord.ui.select(placeholder="Роли", custom_id="select_role_2", options=options, max_values=1)
        async def role_select(self, interaction_select_2: discord.Interaction, select: discord.ui.Select):
            is2_id = str(interaction_select_2.user.id)
            UID[is2_id].secondary_role = select.values[0]
            view = SelectServerMenu()
            await interaction.edit_original_response(
                content=f"Выбрана роль: {UID[is2_id].secondary_role}. Теперь выберите сервер аккаунта.", view=view)
            await interaction_select_2.response.defer()

    class SelectServerMenu(discord.ui.View):
        @discord.ui.select(placeholder="Select", custom_id="select_role_3", options=server_options, max_values=1)
        async def role_select(self, interaction_select_3: discord.Interaction, select: discord.ui.Select):
            is3_id = str(interaction_select_3.user.id)
            UID[is3_id].server_data = select.values[0]
            UID[is3_id].required_icon = choose_random_icon()
            view = CheckIconButton()
            await interaction.edit_original_response(
                content=f"Сервер {UID[is3_id].server_data}! Пожалуйста, измените свою иконку на "
                        f"{ICON_DICT[UID[is3_id].required_icon]}, затем нажмите на кнопку.", view=view)
            await interaction_select_3.response.defer()

    class CheckIconButton(discord.ui.View):
        @discord.ui.button(label="Готово", style=discord.ButtonStyle.primary)
        async def check_icon_1(self, interaction_check_button: discord.Interaction, button: discord.ui.Button):
            icb_id = str(interaction_check_button.user.id)
            try:
                current_icon_id = str(get_summoner_info_by_puuid(UID[icb_id].server_data, UID[icb_id].account_puuid)['profileIconId'])
                if current_icon_id == UID[icb_id].required_icon:  # Если иконка при нажатии кнопки совпадает с требуемой -> True
                    send_data_to_db(icb_id)
                    await interaction_check_button.response.send_message(content="✅ Регистрация завершена.",
                                                                         ephemeral=True, delete_after=float(10))
                    await interaction.delete_original_response()
                else:
                    await interaction.edit_original_response(content=f'⚠️ Ошибка, неверная иконка. Пожалуйста, измените'
                                                                     f' свою иконку на {ICON_DICT[UID[icb_id].required_icon]},'
                                                                     f' затем нажмите на кнопку \'Готово\'.', view=CheckIconButton())
                    await interaction_check_button.response.defer()
            except sqlite3.IntegrityError:  # Эта ошибка выползает если discord_id пользователя в бд уже есть
                await interaction_check_button.response.send_message(content=f"❌ Вы уже регистрировались.",
                                                                     ephemeral=True, delete_after=float(10))
                await interaction.delete_original_response()

    start_view = TextInputView()  # Самый первый view, после него выводятся по порядку
    await interaction.response.send_message("Нажмите на кнопку для начала регистрации.", view=start_view,
                                            ephemeral=True)


@bot.event  # Этот ивент нужен для подгрузки команды через bot.tree.command
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}!')


bot.run(TOKEN)
