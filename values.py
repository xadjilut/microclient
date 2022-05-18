import os.path
import secrets
from os.path import normpath, exists

import pytz as pytz
from hypercorn import Config

config = Config()

if not os.path.exists("secret_key.txt"):
    with open("secret_key.txt", 'wb') as f:
        secret_key_env = os.environ.get("SECRET_KEY")
        if secret_key_env:
            f.write(int.to_bytes(int('0x'+secret_key_env[:32], 16), 16, 'big'))
        else:
            f.write(secrets.token_bytes(16))
with open("secret_key.txt", 'rb') as f:
    secret_key = f.read()

# put your timezone
my_tz = pytz.timezone('Europe/Moscow')

current_sessions = {}
cidrs = {}


n = '\n'
t = '/armyrf'
dlpath = 'static/dl/'
if not exists(normpath(dlpath)):
    os.makedirs(normpath(dlpath), exist_ok=True)
uploadpath = 'static/upload/'
if not exists(normpath(uploadpath)):
    os.makedirs(normpath(uploadpath), exist_ok=True)
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
faqtext = f"""<h3>Это безопасно?</h3><br>
<img src='http://murix.ru/0/2Q.gif'/></br><br>Вполне, но только в случае самостоятельной установки данного 
приложения на домашнем ПК, удалённом сервере, либо используя для установки услуги проверенных хостинг-провайдеров. 
Никто не гарантирует сохранность твоего аккаунта, если ты заюзаешь микроклиент, установленный на 
незнакомом тебе сайте.</br><h2>Впрочем...</h2><br>Испытать удачу и авторизоваться в тапкофоне, используя 
фейковый аккаунт, ты можешь на официальном сайте: <code>murix.ru/armyrf</code>.</br><h1>Как установить?</h1><br>
Самый простой способ - это накатить на Heroku (требуется регистрация): 
<a href='https://heroku.com/deploy?template=https://github.com/xadjilut/microclient'>
<img src='https://www.herokucdn.com/deploy/button.png'/></a></br><br>Более подробный мануал в 
<a href='https://github.com/xadjilut/microclient'>официальном репо</a>.</br>
<br><i>(будет дополняться)</i></br><p><a href='{t}'>понятно</a> <a href='{t}/wat'>непонятно</a></p>
"""
tgevents = '<h1>777000</h1>Telegram Events'
passform = "<form action='%' method='post'><input type='password' name='password' /><input type='submit' value='ок' " \
           "/></form> "
authform = "<form action='' method='post'><input type='{type}' name='{name}' /><input " \
           "type='submit' value='{button}' /></form>"
form = "<form action='' method='post'><input type='text' name='message' /><input type='submit' value='»' /></form>"
fileform = "<form action='' method='post' enctype='multipart/form-data'><input type='file' name='file' /><input " \
           "type='submit' value='Speak' /></form> "
