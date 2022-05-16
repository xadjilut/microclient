import datetime
import logging
import os.path
from functools import wraps
from time import time

from quart import redirect, request, url_for, Response, session, g
from quart_rate_limiter import rate_limit
from telethon import TelegramClient, errors
from telethon.sessions import SQLiteSession, StringSession

from helper import api_id, api_hash, check_cookies, decrypt_session_string, aeskey, new_cookies, check_phone, \
    check_bot_token, encrypt_session_string, get_client_ip
from micrologging import log
from values import secret_key, current_sessions, temp, authform, t, passform, app

if os.path.exists("session.session"):
    guest_client = TelegramClient('session', api_id, api_hash)
    guest_client.start()
else:
    try:
        guest_auth_key = os.environ.get("GUEST_AUTH_KEY")
        if guest_auth_key:
            guest_client = TelegramClient(StringSession(guest_auth_key), api_id, api_hash)
        else:
            guest_client = TelegramClient(StringSession(), api_id, api_hash)
            raise Exception()
        guest_client.start()
    except:
        print("Guest account session is not set\n")


def auth_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logging.info(f"{get_client_ip(request.headers)} - {func.__name__}: {args}, {kwargs}")
        _sess_id = request.cookies.get("_sess_id")
        if request.cookies.get('_guest', '1') == '1' and guest_client.session.auth_key:
            g.__setattr__(f"client{_sess_id}", guest_client)
            session[f"client_id"] = f"client{_sess_id}"
            return await func(*args, **kwargs)
        try:
            _sess = request.cookies.get('_sess')
            norm_cookies = check_cookies(
                _sess,
                get_client_ip(request.headers),
                request.user_agent.string,
                int(_sess_id) if _sess_id else 0
            )
            await decrypt_session_string(
                request.cookies.get("varstr"),
                secret_key, aeskey, _sess,
                int(_sess_id) if _sess_id else 0
            )
            if not norm_cookies:
                if request.cookies.get('conststr'):
                    return redirect(url_for("password"))
                raise Exception("not norm cookies and nullable conststr")
        except Exception as e:
            log(f"auth_required: {e}")
            if request.cookies.get("conststr"):
                return redirect(url_for("password"))
            return redirect(url_for('auth'))
        return await func(*args, **kwargs)

    return wrapper


@app.route(f"{t}/auth", methods=['GET', 'POST'])
@rate_limit(3, datetime.timedelta(seconds=3))
@rate_limit(20, datetime.timedelta(minutes=5))
async def auth():
    mode = request.args.get("mode")
    if mode:
        resp = Response("...открываю гостевой акк...")
        if mode == 'guest':
            resp.set_cookie('_guest', "1", 1)
        elif mode == 'norm':
            resp.set_cookie('_guest', '0', 60 * 60 * 24 * 90)
        resp.headers['Location'] = url_for('hello')
        return resp, 302
    if request.cookies.get('conststr'):
        return redirect(url_for("hello"), 307)
    resp = Response('')
    _sess = request.cookies.get("_sess")
    if not _sess:
        _sess_id = time().__hash__() ^ 4815162342
        resp.set_cookie("_sess_id", str(_sess_id), 60 * 60 * 24 * 17)
        _sess = new_cookies(get_client_ip(request.headers), request.user_agent.string, _sess_id)
        resp.set_cookie("_sess", _sess, 60 * 60 * 24 * 17)
    if request.args.get('reset') == '1' and _sess in current_sessions:
        del current_sessions[_sess]
        return redirect(url_for('auth'))
    current = current_sessions.get(_sess)
    if not current:
        current_sessions[_sess] = {"expires_in": int(time()) + 60 * 15}
        current = current_sessions[_sess]
    error = ''
    if request.method == 'POST':
        if 'stage' not in current:
            return redirect(url_for('auth', _method='GET'), 307)
        request_form = await request.form
        phone = request_form.get('phone')
        code = request_form.get("code")
        pass2fa = request_form.get("2fa")
        try:
            if phone:
                if check_phone(phone):
                    client = TelegramClient(SQLiteSession(), api_id, api_hash)
                    await client.connect()
                    await client.send_code_request(phone)
                    current['client'] = client
                    current['stage'] = 'code' + phone
                elif check_bot_token(phone):
                    client = TelegramClient(SQLiteSession(), api_id, api_hash)
                    await client.start(bot_token=phone)
                    current['client'] = client
                    current['stage'] = 'pass'
                else:
                    raise Exception("invalid number or bot token")
            elif code and current['stage'][:4] == 'code':
                client: TelegramClient = current['client']
                await client.sign_in(current['stage'][4:], code=code)
                current['client'] = client
                current['stage'] = 'pass'
            elif pass2fa and current['stage'][:3] == '2fa':
                client: TelegramClient = current['client']
                await client.sign_in(current['stage'][3:], password=pass2fa)
                current['client'] = client
                current['stage'] = 'pass'
        except errors.PhoneCodeExpiredError as e:
            log(f'auth: {e}')
            error = '<i><b>Код истёк, начни авторизацию заново</b></i>'
        except errors.PhoneCodeInvalidError as e:
            log(f'auth: {e}')
            error = '<i><b>Неверный код, пробуй ещё...</b></i>'
        except errors.SessionPasswordNeededError:  # requires 2fa password
            current['stage'] = '2fa' + current['stage'][4:]
        except errors.PasswordHashInvalidError as e:
            log(f'auth: {e}')
            error = '<i><b>Неверный пароль 2fa, попробуй снова...</b></i>'
        except errors.FloodWaitError as e:
            log(f'auth: {e}')
            error = f'<i><b>Ага, довыёбывался, теперь жди {e.seconds} сек.</b></i>'
        except Exception as e:
            log(f"auth: {e}")
            error = f'<i><b>Произошла ошиб очка: {e}</b></i>'
    text = "<img src='http://murix.ru/0/2Q.gif'/>"
    if 'stage' not in current or current.get('stage') == 'phone':
        text += "<h3>Введи номер...</h3>" + authform.format(
            type='text', name='phone', button='»'
        ) + f' {error}<br>Либо используй <a href="{t}/auth?mode=guest">гостевой аккаунт</a>'
        if 'stage' not in current:
            current_sessions[_sess] = {"stage": "phone", 'client': None}
    elif current['stage'][:4] == 'code':
        text += "<h3>Введи код...</h3>" + authform.format(
            type='text', name='code', button='ок'
        ) + f' {error}<br><a href="{t}/auth?reset=1">назад</a>'
    elif current['stage'][:3] == '2fa':
        text += "<h3>Введи пароль 2fa...</h3>" + authform.format(
            type='password', name='2fa', button='ок'
        ) + f' {error}<br><a href="{t}/auth?reset=1">назад</a>'
    elif current['stage'] == 'pass':
        client = current['client']
        async with client:
            session_string, _ = encrypt_session_string(client, secret_key, aeskey)
            resp.set_cookie(
                "varstr",
                session_string,
                60 * 60 * 24 * 3
            )
        del current_sessions[_sess]
        _sess_id = time().__hash__() ^ 4815162342
        resp.set_cookie("_sess_id", str(_sess_id), 60 * 60 * 24 * 17)
        _sess = new_cookies(get_client_ip(request.headers), request.user_agent.string, _sess_id)
        resp.set_cookie("_sess", _sess, 60 * 60 * 24 * 17)
        current_sessions[_sess] = {"client": client, "expires_in": 60 * 10, "stage": "pass"}
        hint = '<i>С доп. паролем ты сможешь долго оставаться в системе и вообще это для защиты твоих бесед</i>'
        text += f'<h3>Установи доп. пароль</h3>{passform.replace("%", f"{t}/pass?set=1")} {error}<p>{hint}</p>' \
                f'<a href="{t}">продолжить без пароля</a>'
    resp.set_data(temp.replace('%', text))
    return resp


@app.route(f"{t}/pass", methods=['GET', 'POST'])
@rate_limit(3, datetime.timedelta(seconds=3))
@rate_limit(7, datetime.timedelta(minutes=1))
async def password():
    error = ''
    if request.method == 'POST':
        request_form = await request.form
        if request_form.get("password"):
            try:
                resp = Response(temp.replace('%', 'принято, перебрасываю в тапкофон...'))
                _sess = request.cookies.get('_sess')
                _sess_id = request.cookies.get('_sess_id')
                password_encoded = request_form.get("password").encode()
                client_id = f"client{_sess_id}"
                if request.args.get('set') == '1' and _sess in current_sessions \
                        and current_sessions[_sess].get("stage") == 'pass':
                    client = current_sessions[_sess].pop('client')
                    g.__setattr__(client_id, client)
                    conststr, _const_id = encrypt_session_string(client, password_encoded, secret_key, is_const=True)
                    resp.set_cookie(
                        'conststr',
                        conststr,
                        60 * 60 * 24 * 17
                    )
                    resp.set_cookie(
                        "_const_id",
                        str(_const_id),
                        60 * 60 * 24 * 17
                    )
                else:
                    _sess_id = time().__hash__() ^ 4815162342
                    _const_id = request.cookies.get("_const_id", '0')
                    await decrypt_session_string(
                        request.cookies.get("conststr"),
                        password_encoded,
                        secret_key,
                        _sess, _sess_id, int(_const_id)
                    )
                    client = current_sessions[_sess].get('client')
                    varstr, _ = encrypt_session_string(client, secret_key, aeskey)
                    resp.set_cookie(
                        "varstr",
                        varstr,
                        60 * 60 * 24 * 3
                    )
                    resp.set_cookie("_sess_id", str(_sess_id), 60 * 60 * 24 * 17)
                    _sess = new_cookies(get_client_ip(request.headers), request.user_agent.string, _sess_id)
                    resp.set_cookie("_sess", _sess, 60 * 60 * 24 * 17)
                resp.headers['Location'] = url_for("hello")
                return resp, 302
            except Exception as e:
                log(f"password: {e}")
                error += '<b><i>Неверный пароль, попробуй снова либо выйди и авторизуйся заново</i></b>'
    return temp.replace(
        '%', f'<h3>Введи пароль</h3><br>{passform.replace("%", "")} {error}<br><a href="{t}/logout">выйти</a>'
    )


@app.route(f'{t}/logout')
@rate_limit(3, datetime.timedelta(seconds=3))
# @auth_required
async def logout():
    _sess = request.cookies.get('_sess')
    if _sess in current_sessions:
        client: TelegramClient = current_sessions[_sess]['client']
        if client:
            await client.connect()
            await client.log_out()
        del current_sessions[_sess]
    resp = Response(temp.replace('%', 'ок, перебрасываю в авторизацию...'))
    resp.set_cookie("varstr", '', 1)
    resp.set_cookie("conststr", '', 1)
    resp.set_cookie("_guest", '0', 60 * 60 * 24 * 90)
    resp.headers['Location'] = url_for("auth")
    return resp, 302
