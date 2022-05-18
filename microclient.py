# by XADJILUT, 2020-2022
import asyncio
import base64
import datetime
import io
import logging
import time
from asyncio import sleep
from html import escape
from os.path import exists, normpath
from urllib.request import urlopen, Request

import hypercorn.asyncio
import pyaes
from boilerpy3.extractors import KeepEverythingExtractor as CanolaExtractor
from pydub import AudioSegment
from quart import request, redirect, url_for, send_file, session, g, Quart
from quart_rate_limiter import rate_limit, RateLimiter
from telethon import TelegramClient
from telethon.tl.types import User, MessageMediaDocument, Document, DocumentAttributeAudio, DocumentAttributeFilename
from werkzeug.utils import secure_filename

from authorization import auth_required, auth, password, logout
from helper import put_message_head, put_content, saltkey, hello_everybot, aeskey, get_title_or_name, pack_xid, \
    xid2id, unpack_xid, guest_client
from ipworker import IpWorker
from micrologging import microlog
from values import my_tz, temp, t, config, fileform, form, dlpath, current_sessions, tgevents, wattext, \
    faqtext, secret_key, uploadpath

app = Quart(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=1)
app.url_map.strict_slashes = False
app.secret_key = secret_key

rate_limiter = RateLimiter(app)


@app.route('/')
async def alias():
    return redirect(url_for('hello'), 307)


# main page
@app.route(t)
@rate_limit(3, datetime.timedelta(seconds=3))
@auth_required
async def hello():
    client: TelegramClient = g.__getattr__(session['client_id'])
    me = await client.get_me()
    text = f'<p><a href="{t}/profile">{get_title_or_name(me)}</a></p>'
    offset = request.args.get("offset", '0')
    if offset.isnumeric():
        offset = int(offset)
    else:
        offset = 0
    text += f'<h3>Выбери чат...</h3><br><a href="{t}/wat">шта?</a>'
    i = -1
    async for x in client.iter_dialogs(limit=50+offset):
        i += 1
        if i < offset or x.entity.id == me.id:
            continue
        mentions = ''
        xid = pack_xid(
            x.entity.id, getattr(x.input_entity, 'access_hash', -1488), x.is_user
        )
        if x.unread_mentions_count > 0:
            mentions = f'<b><a href="{t}/search/{xid}?mentions={x.unread_mentions_count}">' \
                       f'{x.unread_mentions_count}</a> @</b> '
        if x.entity.id != 777000 or client != guest_client:
            text += f'<br><a href="{t}/{xid}">{escape(x.name)}</a> {mentions}(<a href="{t}/{xid}' \
                    f'?offset={x.unread_count}">{x.unread_count})</a>'
    text += '<br><br>'
    if offset:
        text += f'<a href="{t}?offset={offset-50}">{escape("<<<")}</a> '
    if i > offset:
        text += f'<a href="{t}?offset={offset+50}">{escape(">>>")}</a>'
    return temp.replace('%', text)


@app.route(f'{t}/profile')
@auth_required
async def profile():
    client: TelegramClient = g.__getattr__(session['client_id'])
    me = await client.get_me()
    text = f'<p><b>{get_title_or_name(me)}</b><br>'
    if request.cookies.get("_guest", "1") == '1':
        if request.cookies.get("varstr"):
            text += f'<a href="{t}/auth?mode=norm">в свой аккаунт...</a>'
        else:
            text += f'<a href="{t}/logout">авторизоваться</a>'
    else:
        text += f'<a href="{t}/auth?mode=guest">в гостевой аккаунт...</a>' \
                f'<br><a href="{t}/logout">выйти</a>'
    text += '</p>'
    return temp.replace('%', text)
    pass


@app.route(f'{t}/wat')
def wat():
    return temp.replace('%', wattext)


@app.route(f'{t}/faq')
def faq():
    return temp.replace('%', faqtext)


@app.route(f'{t}/<int:xid>', methods=['GET', 'POST'])
@rate_limit(3, datetime.timedelta(seconds=3))
@rate_limit(30, datetime.timedelta(minutes=3))
@auth_required
async def dialog(xid):
    flag, resp = hello_everybot()
    entity_id = xid2id(xid)
    client: TelegramClient = g.__getattr__(session['client_id'])
    if entity_id == 777000 and client == guest_client:
        return temp.replace('%', tgevents)
    if flag and request.args.get("message_id"):
        return resp
    error = ''
    check = request.args.get("check")
    pagindict = {'reverse': False}
    message_id = request.args.get('message_id')
    peer = unpack_xid(xid)
    try:
        entity = await client.get_entity(peer)
    except Exception as e:
        logging.info(f"peer not found - {e}")
        return temp.replace('%', "<h1>404</h1>Peer not found")
    try:
        if request.method == 'POST':
            request_form = await request.form
            if request_form.get('message'):
                await client.send_message(
                    peer,
                    request_form.get('message'),
                    reply_to=0 if not request_form.get('message_id') else int(request_form.get('message_id'))
                )
                await sleep(0.404)
                return redirect(url_for('dialog', xid=xid, check=True))
    except Exception as e:
        error += f'<b><i>хуйня, давай по-новой!.. {e}</i></b>'
    try:
        limit = request.args.get('offset')
        page = request.args.get('page')
        if page:
            pagindict['reverse'] = True
            pagindict.update({'add_offset': 25 - (int(page) * 25), 'min_id': 1})
        else:
            if limit:
                pagindict.update({'add_offset': int(limit) - 25})
            if message_id and not check:
                pagindict['reverse'] = True
                pagindict.update({'min_id': int(message_id) - 1})
        resp = await client.get_messages(entity, 25, **pagindict)
    except Exception as e:
        return temp.replace('%', f'<h1>Wrong, sorry!</h1>{e}')
    text = ''
    texthead = '<h3>' + get_title_or_name(entity) if not getattr(entity, 'deleted', 0) else ''
    texthead += f'</h3><br><a href="{t}/search/{xid}">поиск.</a><br>{form} {error}'
    for x in resp:
        tmptext = f'''<br><div id="{x.id}">
{await put_message_head(x, xid)}
{await put_content(x, client, True)}<br>
<a href="{t}/reply?xid={xid}&message_id={x.id}">отв.</a> 
<a href="{t}/reply?xid={xid}">чат.</a>
</div>'''
        text = (tmptext + text if not pagindict['reverse'] and not check else text + tmptext)
    text = texthead + text
    return temp.replace('%', text)


@app.route(f'{t}/dl/', methods=['GET', 'POST'])
@rate_limit(5, datetime.timedelta(seconds=10))
@auth_required
async def dl():
    mediastr = base64.b64decode((await request.form).get('media').encode('UTF-8'))
    media = None
    i = 0
    while 1:
        if i >= 2:
            return temp.replace('%', "<h3>Сеанс загрузки истёк</h3><p>Вернись, обнови страницу и повтори снова.</p>")
        crypt = pyaes.AESModeOfOperationCTR(saltkey(aeskey, False if i == 0 else True))
        _mediastr = crypt.decrypt(mediastr).decode(errors="ignore")
        try:
            media = eval(_mediastr)
        except Exception as e:
            logging.info(e)
            i += 1
            continue
        mediastr = _mediastr
        break
    media.document.file_reference = base64.b64decode((await request.form).get('fileref').encode('UTF-8'))
    file = f'{media.document.dc_id}_{media.document.id}'
    if exists(normpath(dlpath + file + '.mp3')):
        return temp.replace('%', f'<a href="{t}/dl/{file}.mp3">{file}.mp3</a><p>{mediastr}')
    client: TelegramClient = g.__getattr__(session['client_id'])
    input = await client.download_media(media, bytes)
    # for voice convert to mp3
    input = io.BytesIO(input)
    input.seek(0)
    segment = AudioSegment.from_file(input)
    segment.export(f"{normpath(dlpath+file)}.mp3", "mp3", bitrate="128k", codec="libmp3lame")
    if exists(normpath(dlpath + file + '.mp3')):
        return temp.replace('%', f'<a href="{t}/dl/{file}.mp3">{file}.mp3</a><p>{mediastr}')
    return temp.replace('%', str(media.document.file_reference))


@app.route(f'{t}/dl/<path:filename>', methods=['GET', 'POST'])
async def dl_path(filename):
    return await send_file(normpath(dlpath + secure_filename(filename)), attachment_filename=filename)


@app.route(f'{t}/reply', methods=['GET', 'POST'])
@rate_limit(3, datetime.timedelta(seconds=3))
@auth_required
async def reply():
    xid = int(request.args.get('xid'))
    entity_id = xid2id(xid)
    client: TelegramClient = g.__getattr__(session['client_id'])
    if entity_id == 777000 and client == guest_client:
        return temp.replace('%', tgevents)
    message_id = request.args.get('message_id')
    peer = unpack_xid(xid)
    if request.method == 'POST':
        voice = (await request.files).get('file')
        if voice:
            try:
                segment = AudioSegment.from_file(voice)
            except Exception as e:
                logging.info(e)
                return temp.replace('%', '<h3>Это не медиа!</h3><p>Чё ахуели там?..</p>')
        logging.info(str(voice))
        if voice and voice.filename:
            path = normpath(uploadpath + secure_filename(voice.filename) + '.ogg')
            segment.export(path, "ogg", bitrate="48k", codec="libopus")
            if exists(path):
                await client.send_file(
                    peer, path, voice_note=True,
                    reply_to=(0 if not message_id else int(message_id))
                )
        return redirect(url_for('dialog', xid=xid, message_id=message_id), code=307)
    text = f'''<h3>{"Oтвети" if message_id else "Написа"}ть в чат..</h3><br><a href="{t}/search/{xid}">поиск.</a>
<br><form action="" method="post"><p><textarea type='text' name='message' rows'3' cols='15'></textarea></p>
<input type="hidden" name="message_id" value="{(message_id if message_id is not None else 0)}" />
<p><input type="submit" value='»' /></p></form><p>
{fileform}</p><br>{"" 
if not message_id else await put_content((await client.get_messages(peer, ids=[int(message_id)]))[0], client)}'''
    return temp.replace('%', text)


# for opening pm dialogs and searching by username
@app.route(f'{t}/search', methods=['GET', 'POST'])
@app.route(f'{t}/search/<string:entity_str>', methods=['GET', 'POST'])
@rate_limit(5, datetime.timedelta(seconds=10))
@auth_required
async def search(entity_str=''):
    client: TelegramClient = g.__getattr__(session['client_id'])
    if not entity_str:
        entity_str = request.args.get("entity", 'me')
    if not entity_str.isnumeric():
        entity = await client.get_entity(entity_str)
        xid = pack_xid(entity.id, entity.access_hash, isinstance(entity, User))
        return redirect(url_for('dialog', xid=xid))
    xid = int(entity_str)
    entity_id = xid2id(xid)
    if entity_id == 777000 and client == guest_client:
        return temp.replace('%', tgevents)
    res = ''
    results = []
    mentions = request.args.get('mentions')
    peer = unpack_xid(xid)
    if mentions is not None:
        results = await client.get_messages(peer, int(mentions), search='@')
    elif request.method == 'POST':
        results = await client.get_messages(peer, 25, search=(await request.form).get('message'))
    for x in results:
        res += f'<div id={x.id}><a href="{t}/{xid}?message_id={x.id}&offset=25">' \
               f'{"<i>Message</i>" if not x.raw_text else x.raw_text[:20]}</a></div><p>'
    return temp.replace('%', f'<b>Чё ищем?</b><br>{form}<p>{res}')


# proxy (work with variable success)
@app.route('/p')
@rate_limit(15, datetime.timedelta(minutes=1))
def proxy():
    url = request.full_path[5:]
    logging.info(''.join(request.full_path))
    domain = url.strip('/').split('://')[-1].split('/')[0].split(':')[0]
    if domain in ['t.me', 'telegram.me']:
        if '/addtheme/' not in url and '/c/' not in url:
            return redirect(url_for("search", entity=url), 307)
    if (IpWorker.is_ip(domain) and IpWorker.ip_spec_contains(domain)) \
            or request.url_root.strip('/').split('://')[-1] in url:
        return temp.replace('%', 'Prevented url, try again')
    try:
        r = Request(url)
        for k, v in request.headers.items():
            if k in ["User-Agent", "Accept"]:
                r.add_header(k, v)
        f = urlopen(r)
        text = f.readlines()
        html = ''.join([x.decode(errors='ignore') for x in text])
    except Exception as e:
        return temp.replace('%', '<h3>Wrong url, try again</h3>' + str(e))
    ehtml = CanolaExtractor().get_doc(html)
    return temp.replace('%', ehtml.content.replace('\n', '<br>'))


# client's user-agent
@app.route('/ua')
def user_agent():
    return temp.replace('%', str(request.headers))


# server time
@app.route('/time')
def curtime():
    return temp.replace('%', datetime.datetime.now(my_tz).strftime('%H:%M:%S<br>%Y-%h-%d'))


async def main():
    await hypercorn.asyncio.serve(app, config)


async def clean_sessions_loop():
    while True:
        await sleep(60 * 20)
        i = 0
        sessions = [x for x in current_sessions.keys()]
        for sess in sessions:
            expires_in = current_sessions[sess].get('expires_in')
            if expires_in and time.time() > expires_in:
                del current_sessions[sess]
                i += 1
        if i:
            logging.info(f"complete sessions cleaning, {i} sessions are removed")


app.add_url_rule(f"{t}/auth", view_func=auth, methods=['GET', 'POST'])
app.add_url_rule(f"{t}/pass", view_func=password, methods=['GET', 'POST'])
app.add_url_rule(f'{t}/logout', view_func=logout)
app.add_url_rule('/microlog/<string:secret_part>', view_func=microlog)

print(f"microclient is started\n")
print(f"Aeskey for debug (base64): {base64.b64encode(aeskey).decode()}")
print(f"Secret key (base64): {base64.b64encode(secret_key).decode()}\n")

if __name__ == '__main__':
    guest_client.loop.create_task(clean_sessions_loop())
    guest_client.loop.run_until_complete(main())
else:
    loop = guest_client.loop
    asyncio.set_event_loop(loop)
    loop.create_task(clean_sessions_loop())
    loop.run_until_complete(main())
