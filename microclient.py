# by XADJILUT, 2020-2021

import asyncio
import base64
import datetime
import hypercorn.asyncio
import io
import pyaes
import random
import re
import sys
from boilerpy3.extractors import KeepEverythingExtractor as CanolaExtractor
from datetime import timedelta
from hypercorn.config import Config
from quart import Quart, request, redirect, url_for, send_file, send_from_directory, make_response
from markupsafe import escape
from PIL import Image
from pydub import AudioSegment
from os.path import exists, realpath
from telethon import TelegramClient, sync
from telethon.tl.types import User, MessageMediaPhoto, MessageMediaDocument, User, Document, DocumentAttributeAudio, DocumentAttributeFilename, MessageEntityUrl, MessageEntityTextUrl
from time import sleep, time
from urllib.request import urlopen, Request
from values import api_id, api_hash
from werkzeug.utils import secure_filename

config = Config()
config.bind = ["0.0.0.0:8090"]

app = Quart(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024

# found session file before using
client = TelegramClient('session', api_id, api_hash)

aeskey = base64.b64decode(sys.argv[1].encode()) if len(sys.argv) == 2 else bytes([random.randint(0,255) for _ in range(16)])

@app.before_serving
async def startup():
    await client.connect()

@app.after_serving
async def cleanup():
    await client.disconnect()

n = '\n'
t = '/armyrf'
dlpath = realpath('static/dl/')
meta = '<meta property="og:title" content="телега для тапика"><meta property="og:site_name" content="/ArmyRF"><meta property="og:description" content="Микроклиент для всех. Вопросы и предложения -> @microclient"><meta property="og:image" content="https://murix.ru/0/h8.jpg"><meta property="og:image:width" content="240"><meta property="og:image:height" content="180">'
temp = f"<html><head><meta charset='utf-8'><title>телега для тапика</title>{meta}<link rel=\"shortcut icon\" href=\"https://murix.ru/0/hU.ico\"></head><body>%</body></html>"
form = "<form action='' method='post'><input type='text' name='message' /><input type='submit' value='»' /></form>"
fileform = "<form action='' method='post' enctype='multipart/form-data'><input type='file' name='file' /><input type='submit' value='Speak' /></form>"

def log(string):
    with open('microlog', 'a') as f:
        f.write(string + '\n')

# for most angry search engine bots
def hello_everybot():
    useragent = request.headers.get('User-Agent')
    if 'Googlebot' in useragent:
        return True, temp.replace('%', 'Hi, Googlebot!')
    elif 'YandexBot' in useragent:
        return True, temp.replace('%', 'Hello, YandexBot!')
    return False, None

# main page
@app.route(t)
async def hello():
#    flag, resp = hello_everybot()
#    if flag: return resp
    check = False
    resp = await client.get_dialogs()
    text = f'<h3>Выбери чат...</h3><br><a href="{t}/wat">шта?</a>'
    for x in resp:
        mentions = ('' if x.unread_mentions_count==0 else f'<b><a href="{t}/search/{x.entity.id}?mentions={x.unread_mentions_count}">{x.unread_mentions_count}</a> @</b> ')
        text += f'<br><a href="{t}/{x.entity.id}">{escape(x.name)}</a> {mentions}(<a href="{t}/{x.entity.id}?offset={x.unread_count}">{x.unread_count})</a>'
    return temp.replace('%', text)

@app.route(t+'/wat')
def wat():
    return temp.replace('%', """<h3>Что за дичь?</h3><br>Это - самопальный веб-клиент Телеграма
, созданный для самых слабеньких и стареньких браузеров. Создан для таких браузеров, которые, 
например, стоят на кнопочных телефонах.<br><h2>Но зачем?</h2><br>История данного клиента 
начинается с середины 2020-ого года. Тогда я ещё служил в армии и думал, как бы хорошо написать 
телегу для кнопочного телефона (а ведь именно такие нам разрешали использовать в части). Так, 
понемногу, потихоньку, да и написал что-то и поднял на вдске.<h1>Ахуеть!</h1><br>Остались 
вопросы, предложения по данному проекту - пиши в телегу @xadjilut или напрямую в 
<a href=/armyrf/search/xadjilut>микроклиенте</a>.<br>murix, 2020-2021
""")

@app.route(t+'/<int:entity_id>', methods=['GET','POST'])
async def dialog(entity_id):
    flag, resp = hello_everybot()
    if flag and request.args.get("message_id"): return resp
    error = ''
    check = False
    pagindict = {'reverse':False}
    message_id = request.args.get('message_id')
    try:
        if request.method == 'POST':
            check = True
            if (await request.form).get('message'):
                await client.send_message(entity_id, (await request.form).get('message'), reply_to=(0 if not (await request.form).get('message_id') else int((await request.form).get('message_id'))))
    except Exception as e:
        error += f'<b><i>хуйня, давай по-новой!.. {str(e)}</i></b>'
    try:
        entity = await client.get_entity(entity_id)
        if request.method == 'POST':
            sleep(0.404)
        limit = request.args.get('offset')
        page = request.args.get('page')
        if page:
            pagindict['reverse'] = True
            pagindict.update({'add_offset':25-(int(page)*25), 'min_id':1})
        else:
            if limit:
                pagindict.update({'add_offset':int(limit)-25})
            if message_id and not check:
                pagindict['reverse'] = True
                pagindict.update({'min_id':int(message_id)-1})
        resp = await client.get_messages(entity_id, 25, **pagindict)
    except Exception as e:
        return temp.replace('%', '<h1>Wrong, sorry!</h1><br>'+str(e))
    text = ''
    texthead = f'<h3>{entity.first_name + (entity.last_name if entity.last_name else "") if entity.__class__ == User else entity.title}</h3><br><a href="{t}/search/{entity_id}">поиск.</a><br>{form} {error}'
    for x in resp:
        tmptext = f'''<br><div id="{x.id}">
{await put_message_head(x, entity_id)}
{await put_content(x, True)}<br>
<a href="{t}/reply?entity_id={entity_id}&message_id={x.id}">отв.</a> 
<a href="{t}/reply?entity_id={entity_id}">чат.</a>
</div>'''
        text = (tmptext+text if not pagindict['reverse'] and not check else text+tmptext)
    text = texthead + text
    return temp.replace('%', text)


async def put_message_head(x, entity_id):
    res = ''
    user = await x.get_sender()
    date = x.date + timedelta(hours=4)
    if user.__class__ == User and not user.is_self:
        res += f'<b>{escape(user.first_name)}{" "+escape(user.last_name) if user.last_name else ""}</b><br>'
    res += f'<i>{date.hour}:{(0 if date.minute<10 else "")}{date.minute} {date.day}.{date.month}.{date.year}</i><p>'
    if x.is_reply:
        y = await x.get_reply_message()
        if not y:
            return res
        user = await y.get_sender()
        if user.__class__ == User:
            resname = f'{escape(user.first_name)}{" "+escape(user.last_name) if user.last_name else ""}'
        else:
            resname = f'{user}'
        if y.raw_text:
            restext = f'<br><i>{escape(y.raw_text[:10])}</i>'
        else:
            restext = f'<br>NotTextMessage'
        res += f'<a href="{t}/{entity_id}?message_id={y.id}"><i>»{resname[:10]}</i>{restext}</a><p>'
    return res


async def put_content(x, limited=None):
    res = ''
    if x.media.__class__ == MessageMediaPhoto:
        mediatype = x.media.photo
        img = f'static/images/{mediatype.dc_id}_{mediatype.id}.jpeg'
        if not exists(img):
            await client.download_media(x, img)
            im = Image.open(img)
            im.thumbnail([128, 128])
            im.save(img, 'JPEG', quality=40)
        res += f'<img src="/{img}"/><p>'
    if x.media.__class__ == MessageMediaDocument:
        mediatype = x.media.document
        mime, ext = mediatype.mime_type.split('/')
        if mime == 'image':
            img = f'static/images/{mediatype.dc_id}_{mediatype.id}'
            if not exists(img+'.jpeg'):
                await client.download_media(x, f'{img}.{ext}')
                im = Image.open(f'{img}.{ext}')
                if im.mode == 'RGBA':
                    im.load() 
                    background = Image.new("RGB", im.size, (255, 255, 255))
                    background.paste(im, mask=im.split()[3])
                    im = background
                im.thumbnail([102, 102])
                im.save(img+'.jpeg', 'JPEG', quality=40)
            res += f'<img src="/{img}.jpeg"/><p>'
        elif mime == 'audio' and ext == 'ogg':
            fileref = base64.b64encode(x.media.document.file_reference).decode('UTF-8')
            x.media.document.file_reference = '&'
            x.media.document.attributes[0].waveform = b''
            crypt = pyaes.AESModeOfOperationCTR(saltkey(aeskey))
            media64 = crypt.encrypt(str(x.media).encode())
            media64 = base64.b64encode(media64).decode('UTF-8')
            res += f'<form action="{t}/dl" method="post"><input type="hidden" name="media" value="{media64}" /><input type="hidden" name="fileref" value="{fileref}" /><input type="submit" value="# ili.!.i|l {x.media.document.attributes[0].duration}s" /></form>'
    if x.message:
        raw = (x.raw_text[:100]+'...' if limited and x.fwd_from else x.raw_text)
        if x.entities is None:
            entities = []
        else:
            entities = x.entities
        rawlist = [(escape(raw) if not entities else escape(raw[:entities[0].offset]))]
        lenent = len(entities)
        for y in range(lenent):
            o = entities[y].offset
            l = entities[y].length
            url = None
            if entities[y].__class__ == MessageEntityUrl:
                url = raw[o:o+l]
            elif entities[y].__class__ == MessageEntityTextUrl:
                url = entities[y].url
            if url is not None:
                rawlist.append(f'<a href="/p?u={url}">{escape(raw[o:o+l])}</a>')
            else:
                rawlist.append(escape(raw[o:o+l]))
            if y + 1 != lenent:
                rawlist.append(escape(raw[o+l:entities[y+1].offset]))
            else:
                rawlist.append(escape(raw[o+l:]))
        res += ''.join(rawlist).replace(n, '<p>')
    return res

# salt aeskey for additional security
def saltkey(aeskey, prev=False):
    base = (int(time()) >> 10) - (1 if prev else 0)
    timestamp = base * 2**10
    al = list(aeskey)
    ai = 0
    while timestamp > 0:
        ii = timestamp % 256
        timestamp //= 256
        al[ai] ^= ii
        ai += 1
    return bytes(al)

@app.route(f'{t}/dl', methods=['GET','POST'])
async def dl():
#    flag, resp = hello_everybot()
#    if flag: return resp
    mediastr = base64.b64decode((await request.form).get('media').encode('UTF-8'))
    i = 0
    while 1:
        if i >= 2: return temp.replace('%', "<h3>Сеанс истёк</h3><p>Вернись, обнови страницу и повтори снова.</p>")
        crypt = pyaes.AESModeOfOperationCTR(saltkey(aeskey, False if i == 0 else True))
        _mediastr = crypt.decrypt(mediastr).decode(errors="ignore")
        try: media = eval(_mediastr)
        except:
            i += 1
            continue
        mediastr = _mediastr
        break
    media.document.file_reference = base64.b64decode((await request.form).get('fileref').encode('UTF-8'))
    file = f'{media.document.dc_id}_{media.document.id}'
    if exists(dlpath+file+'.mp3'):
        return temp.replace('%', f'<a href="{t}/dl/{file}.mp3">{file}.mp3</a><p>{mediastr}')
    input = await client.download_media(media, bytes)
    # for voice convert to mp3
    input = io.BytesIO(input)
    input.seek(0)
    segment = AudioSegment.from_file(input)
    segment.export(f"{dlpath}{file}.mp3", "mp3", bitrate="128k", codec="libmp3lame")
    if exists(dlpath+file+'.mp3'):
        return temp.replace('%', f'<a href="{t}/dl/{file}.mp3">{file}.mp3</a><p>{mediastr}')
    return temp.replace('%', str(media.document.file_reference))


@app.route(f'{t}/dl/<path:filename>', methods=['GET','POST'])
async def dl_path(filename):
    return await send_file(dlpath+secure_filename(filename), attachment_filename=filename)


@app.route(f'{t}/reply', methods=['GET','POST'])
async def reply():
#    flag, resp = hello_everybot()
#    if flag: return resp
    entity_id = int(request.args.get('entity_id'))
    message_id = request.args.get('message_id')
    if request.method == 'POST':
        voice = (await request.files).get('file')
        if voice:
            try: segment = AudioSegment.from_file(voice)
            except: return temp.replace('%', '<h3>Это не медиа!</h3><p>Чё ахуели там?..</p>')
        log(str(voice))
        if voice and voice.filename:
            path = f'static/upload/{secure_filename(voice.filename)}'
            segment.export(f"{path}", "ogg", bitrate="48k", codec="libopus")
            if exists(path):
                await client.send_file(entity_id, path, voice_note=True, reply_to=(0 if not message_id else int(message_id)))
        return redirect(url_for('dialog', entity_id=entity_id, message_id=message_id), code=307)
    text = f'''<h3>{"Oтвети" if message_id else "Написа"}ть в чат..</h3><br><a href="{t}/search/{entity_id}">поиск.</a><br>
               <form action="" method="post"><input type="text" name="message" />
               <input type="hidden" name="message_id" value="{(message_id if message_id is not None else 0)}" />
               <input type="submit" value='»' /></form><p>
               {fileform}<br>{("" if not message_id else await put_content((await client.get_messages(entity_id, ids=[int(message_id)]))[0]))}'''
    return temp.replace('%', text)

# for opening pm dialogs
@app.route(f'{t}/search/',methods=['GET','POST'])
@app.route(f'{t}/search/<string:entity_str>', methods=['GET','POST'])
async def search(entity_str=None):
    try:
        entity_id = int(entity_str)
    except:
        entity = await client.get_entity(entity_str)
        return redirect(url_for('dialog', entity_id=entity.id))
    res = ''
    results = []
    mentions = request.args.get('mentions')
    if mentions is not None:
        results = await client.get_messages(entity_id, int(mentions), search='@')
    elif request.method == 'POST':
        results = await client.get_messages(entity_id, 25, search=(await request.form).get('message'))
    for x in results:
        res += f'<div id={x.id}><a href="{t}/{entity_id}?message_id={x.id}&offset=25">{("<i>Message</i>" if not x.raw_text else x.raw_text[:20])}</a></div><p>'
    return temp.replace('%', f'<b>Чё ищем?</b><br>{form}<p>{res}')

# proxy (work with variable success)
@app.route('/p')
def proxy():
    url = request.full_path[5:]
    log(''.join(request.full_path))
    if re.fullmatch(r"\bhttps?://(?:localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?/?", url) or request.url_root.split('://')[-1] in url:
        return temp.replace('%', 'Prevented url, try again')
    try:
        f = urlopen(url)
        text = f.readlines()
        html = ''.join([x.decode(errors='ignore') for x in text])
    except Exception as e:
        return temp.replace('%', 'Wrong url, try again<br>'+str(e))
    ehtml = CanolaExtractor().get_doc(html)
    return temp.replace('%', ehtml.content.replace('\n', '<br>'))

# client's user-agent
@app.route('/ua')
def useragent():
    return temp.replace('%', str(request.headers))

# server time
@app.route('/time')
def curtime():
    return temp.replace('%', datetime.datetime.now().strftime('%H:%M:%S<br>%d %h %Y'))

async def main():
    await hypercorn.asyncio.serve(app, config)

if __name__ == '__main__':
    print(f"microclient is started\n\nAeskey for debug (base64): {base64.b64encode(aeskey).decode()}\n")
    client.loop.run_until_complete(main())
