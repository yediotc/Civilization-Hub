import os
import requests
import re
import sqlite3

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from flask_openid import OpenID
from datetime import datetime

from addition import *

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///account.db")


STEAM_API_KEY = '33F294F0F071953872911ECEA0C9508C'
STEAM_OPENID_URL = "https://steamcommunity.com/openid"
APP_ID = '289070'
civilization = [1295660, 289070, 8930, 3900, 3910]

player_count = 0
sum_achievement = 0

app = Flask(__name__)
app.secret_key = 'random_secret_key'
oid = OpenID(app)


@app.template_filter('datetimeformat')
def datetimeformat(value):
    return datetime.utcfromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def index():

    if "steam_id" not in session:
        return redirect("/login")

    steam_id = session.get('steam_id')

    if not steam_id:
        apology("Invalid Steam ID", 400)


    profile = get_player_profile(steam_id)
    civ_games = get_owned_games(steam_id)

    if not profile:
        apology("Invalid Steam ID", 400)
    if not civ_games:
        apology("Failed to get owned civilization series games", 400)

    return render_template('index.html', steam_id=steam_id,profile=profile,civ_games=civ_games)


@app.route('/achievement')
@login_required
def achievement():
    steam_id = session.get('steam_id')
    if not steam_id:
        return redirect("/login")

    player_achievements = get_player_achievement(steam_id)
    global_achievements = get_global_achievement()
    profile = get_player_profile(steam_id)
    achievement_count = 0

    achievements_dict = []
    global_achievement_map = {item['name']: item for item in global_achievements}

    for achievement in player_achievements:
        apiname = achievement['apiname']
        global_achievement = global_achievement_map.get(apiname, None)

        if global_achievement:
            achievement['percent'] = global_achievement.get('percent', 0.0)

        if achievement['achieved'] == 1 and 'unlocktime' in achievement:
            achievement['unlocktime'] = datetimeformat(achievement['unlocktime'])
            achievement_count += 1
        else:
            achievement['unlocktime'] = None

        achievement['name'] = achievement.get('name', 'Unknown Achievement')
        achievement['description'] = achievement.get('description', 'No description available.')

        achievements_dict.append(achievement)

    progress = achievement_count / 320
    progress = "{:.2%}".format(progress)

    earliest_achievement = min(
        (a for a in achievements_dict if a['achieved'] == 1),
        key=lambda x: x.get('unlocktime', float('inf')),
        default=None
    )
    rarest_achievement = min(
        (a for a in achievements_dict if a['achieved'] == 1),
        key=lambda x: x.get('percent', 100.0),
        default=None
    )
    return render_template('achievement.html', profile = profile, achievements=achievements_dict, achievement_count = achievement_count,  progress=progress, earliest_achievement=earliest_achievement, rarest_achievement=rarest_achievement)



@app.route('/discuss', methods=['GET', 'POST'])
@login_required
def discuss():
    steam_id = session.get('steam_id')

    if not steam_id:
        return redirect("/login")

    profile = get_player_profile(steam_id)

    if not profile:
        apology("Invalid Steam ID", 400)

    if request.method == "POST":
        comment = request.form.get("comment")

        if not comment:
            flash ("Comment cannot be empty", "danger")
        elif len(comment) < 10:
            flash ("Comment must be at least 10 characters", "danger")
        elif len(comment) > 500:
            flash ("Comment must be less than 500 characters", "danger")
        elif db.execute("INSERT INTO comment (steam_id, username, avatar_url, content) VALUES (?,?, ?, ?)", steam_id, profile['personaname'], profile['avatarfull'], comment):
            flash ("Comment posted successfully", "success")

    comments = db.execute("SELECT * FROM comment")

    return render_template('discuss.html', profile=profile, comments = comments)



@app.route('/news')
def news():
    steam_news = get_news_for_app()
    return render_template('news.html', steam_news=steam_news)


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/start_login')
@oid.loginhandler
def start_login():
    if session.get('steam_id'):
        return redirect(url_for('index'))

    return oid.try_login(STEAM_OPENID_URL, ask_for=['fullname', 'email'])


@oid.after_login
def after_login(resp):
    steam_id = get_steam_id_from_claimed_id(resp.identity_url)
    if steam_id:
        session['steam_id'] = steam_id
        return redirect(url_for('index'))
    else:
        return 'Login failed'

@app.route('/logout')
def logout():
    session.pop('steam_id', None)
    return redirect(url_for('index'))




def get_steam_id_from_claimed_id(claimed_id):
    steam_id_re = re.compile(r'https://steamcommunity.com/openid/id/(.*?)$')
    match = steam_id_re.match(claimed_id)
    return match.group(1) if match else None


if __name__ == '__main__':
    app.run(debug=True)
