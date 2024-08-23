import os
import requests
import re
import sqlite3

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_openid import OpenID

from flask import redirect, render_template, request, session
from functools import wraps

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///account.db")


STEAM_API_KEY = '33F294F0F071953872911ECEA0C9508C'
STEAM_OPENID_URL = "https://steamcommunity.com/openid"
APP_ID = '289070'
civilization = [1295660, 289070, 8930, 3900, 3910]

player_count = 0
sum_achievement = 0

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("steam_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function



def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def get_player_profile (steam_id):
    url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/'
    params = {
        'key': STEAM_API_KEY,
        'steamids': steam_id
    }
    data = requests.get(url, params=params).json()
    return data['response']['players'][0]

def get_friends_list(steam_id):
    url = f'http://api.steampowered.com/ISteamUser/GetFriendList/v0001/'
    params = {
        'key': STEAM_API_KEY,
        'steamid': steam_id,
        'relationship': 'friend'
    }
    data = requests.get(url, params=params).json()
    return data['friendslist']['friends']


def get_owned_games(steam_id):
    url = f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'
    params = {
        'key': STEAM_API_KEY,
        'steamid': steam_id,
        'include_appinfo': 1,
        'include_played_free_games': 0
    }
    data = requests.get(url, params=params).json()
    games = data.get('response', {}).get('games', [])
    civ_games = [game for game in games if game['appid'] in civilization]

    civ_games.sort(key=lambda x: x['appid'], reverse=True)
    return civ_games

def get_news_for_app():
    url = f'http://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/'
    params = {
        'appid': APP_ID,
        'count': 5,
        'maxlength': 300,
        'format': 'json'
    }
    data = requests.get(url, params=params).json()
    news_items = data['appnews']['newsitems']
    news_list = []
    for item in news_items:
        news = {
            'title': item['title'],
            'url': item['url'],
            'contents': item['contents'],
            'date': item['date']  # Unix timestamp
        }
        news_list.append(news)
    return news_list


def get_global_achievement():
    url = f'http://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/'
    params = {
        'gameid': APP_ID
    }
    data = requests.get(url, params=params).json()
    return data['achievementpercentages']['achievements']


def get_player_achievement(steam_id):
    url = f'http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/'
    params = {
        'appid': APP_ID,
        'key': STEAM_API_KEY,
        'steamid': steam_id,
        'l': 'en'
    }
    data = requests.get(url, params=params).json()
    return data['playerstats']['achievements']
