import os.path
import secrets
from datetime import timedelta
from os.path import realpath, exists

import pytz as pytz
from hypercorn import Config
from quart import Quart
from quart_rate_limiter import RateLimiter

config = Config()
config.bind = ["0.0.0.0:8090"]

app = Quart(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.url_map.strict_slashes = False

rate_limiter = RateLimiter(app)

if not os.path.exists("secret_key.txt"):
    with open("secret_key.txt", 'wb') as f:
        f.write(secrets.token_bytes(16))
with open("secret_key.txt", 'rb') as f:
    secret_key = f.read()
    app.secret_key = secret_key

# put your timezone
my_tz = pytz.timezone('Europe/Moscow')

current_sessions = {}
cidrs = {}


n = '\n'
t = '/armyrf'
dlpath = realpath('static/dl/')
if not exists(dlpath):
    os.mkdir(dlpath,)
meta = '<meta property="og:title" content="телега для тапика"><meta property="og:site_name" content="/ArmyRF"><meta ' \
       'property="og:description" content="Микроклиент для всех. Вопросы и предложения -> @armyrfchat"><meta ' \
       'property="og:image" content="https://murix.ru/0/h8.jpg"><meta property="og:image:width" content="240"><meta ' \
       'property="og:image:height" content="180"> '
temp = f"<html><head><meta charset='utf-8'><title>телега для тапика</title>{meta}<link rel=\"shortcut icon\" " \
       f"href=\"https://murix.ru/0/hU.ico\"></head><body>%</body></html> "
wattext = """<h3>Что за дичь?</h3><br>
<img src='http://murix.ru/0/hk.gif'/></br><br>Это - самопальный веб-клиент Телеграма
, созданный для самых слабеньких и стареньких браузеров. Создан для таких браузеров, которые, 
например, стоят на кнопочных телефонах.</br><h2>Но зачем?</h2><br>История данного клиента 
начинается с середины 2020-ого года. Тогда я ещё служил в армии и думал, как бы хорошо написать 
телегу для кнопочного телефона (а ведь именно такие разрешалось использовать в части). Так, 
понемногу, потихоньку, да и написал что-то и поднял на вдске.</br><h1>Ахуеть!</h1><br>Остались вопросы, замечания 
или предложения по данному проекту - пиши в <a href=/armyrf/search/armyrfchat>чат обратной связи</a> микроклиента.
</br><p>Исходный код проекта: <a href='https://github.com/xadjilut/microclient'>
https://github.com/xadjilut/microclient</a></p>
<br>murix, 2020-2022
"""
tgevents = '<h1>777000</h1>Telegram Events'
passform = "<form action='%' method='post'><input type='password' name='password' /><input type='submit' value='ок' " \
           "/></form> "
authform = "<form action='' method='post'><input type='{type}' name='{name}' /><input " \
           "type='submit' value='{button}' /></form>"
form = "<form action='' method='post'><input type='text' name='message' /><input type='submit' value='»' /></form>"
fileform = "<form action='' method='post' enctype='multipart/form-data'><input type='file' name='file' /><input " \
           "type='submit' value='Speak' /></form> "
