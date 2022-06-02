import argparse
import base64
import io
import logging
import os
import random
import re
import sys
from hashlib import md5
from html import escape
from os.path import exists
from time import time
from typing import Tuple
from urllib.request import urlopen

import emoji
import pyaes
from PIL import Image
from quart import request, g, session
from telethon import TelegramClient, sync
from telethon.sessions import StringSession
from telethon.tl.types import User, MessageMediaPhoto, MessageMediaDocument, MessageEntityUrl, MessageEntityTextUrl, \
    Message, TypeInputPeer, InputPeerUser, InputPeerChat, InputPeerChannel, MessageEntityMentionName, \
    MessageEntityMention

from ipworker import IpWorker
from values import t, n, temp, current_sessions, my_tz, config, cidrs, emojipath, client_args


class ArgV:
    api_id: int
    api_hash: str
    aes_key: str
    setup_guest: bool
    bind_address: str
    print_auth_key: str
    worker_class: str


argv = ArgV()

parser = argparse.ArgumentParser("Microclient 4 all devices")
parser.add_argument("--api-id", metavar="API_ID", type=int, default=8411715,
                    help="Optional integer api id from my.telegram.org. Defaults to 8411715")
parser.add_argument("--api-hash", metavar="API_HASH", type=str, default="5d1e64c612152a060197db12f2927871",
                    help="Optional string api hash from my.telegram.org. Defaults to "
                         "\"5d1e64c612152a060197db12f2927871\"")
parser.add_argument("--aes-key", metavar="AES_KEY", type=str, default="",
                    help="Optional string aes key in base64-encoded format. Defaults to pre-generated byte array")
parser.add_argument("--setup-guest", dest="setup_guest", action="store_true",
                    help="Optional argument to setup guest account session")
parser.add_argument("-b", dest="bind_address", default="0.0.0.0:8090", help=argparse.SUPPRESS)  # for hypercorn running
parser.add_argument("--print-auth-key", dest="print_auth_key", action="store_true",
                    help="Optional argument to print auth key after setting up guest account")
parser.add_argument("main_module", nargs="?", default="microclient:app", type=str,
                    help=argparse.SUPPRESS)  # for hypercorn running too
parser.parse_args(namespace=argv)

api_id = os.environ.get("API_ID") or argv.api_id
api_hash = os.environ.get("API_HASH") or argv.api_hash

if argv.setup_guest:
    try:
        with sync.TelegramClient(
                "session" if not argv.print_auth_key else StringSession(), api_id, api_hash, **client_args) as _client:
            if argv.print_auth_key:
                sys.stdout.write(f"Guest auth key: {_client.session.save()}\n")
    except:
        sys.stdout.write("\nOKAY")
        exit(1)
    sys.stdout.write("Guest account session created successfully!\n")
    exit(0)
elif argv.print_auth_key:
    sys.stdout.write("Run with --setup-guest\n")
    exit(0)

if argv.bind_address:
    config.bind = [argv.bind_address]

if os.environ.get("AES_KEY"):
    aeskey = base64.b64decode(os.environ.get("AES_KEY").encode())
elif argv.aes_key:
    aeskey = base64.b64decode(argv.aes_key.encode())
else:
    aeskey = bytes(
        [random.randint(0, 255) for _ in range(16)]
    )

if os.path.exists("session.session"):
    guest_client = TelegramClient('session', api_id, api_hash, **client_args)
    guest_client.parse_mode = "HTML"
    guest_client.start()
else:
    try:
        guest_auth_key = os.environ.get("GUEST_AUTH_KEY")
        if guest_auth_key:
            guest_client = TelegramClient(StringSession(guest_auth_key), api_id, api_hash, **client_args)
        else:
            guest_client = TelegramClient(StringSession(), api_id, api_hash, **client_args)
            raise Exception("Guest account session is not set")
        guest_client.parse_mode = "HTML"
        guest_client.start()
    except:
        sys.stdout.write("Guest account session is not set\n")


def check_cookies(cookies_hash: str, ip: str, user_agent: str, sess_id: int):
    return bool(cookies_hash) and cookies_hash == new_cookies(ip, user_agent, sess_id)


async def decrypt_session_string(cookies_str: str, key1: bytes, key2: bytes,
                                 _sess: str, _sess_id: int, _const_id: int = 0):
    if not cookies_str:
        raise Exception("cookies string is empty")
    current = current_sessions.get(_sess)
    if current and 'client' in current and not _const_id:
        client = current['client']
    else:
        session_string_b64 = cookies_str.encode()
        session_string_cipher = base64.urlsafe_b64decode(session_string_b64)
        if _const_id:
            session_string_lenten = b''
            for i in range(len(session_string_cipher) // 8):
                session_string_lenten += int.to_bytes(
                    int.from_bytes(session_string_cipher[i * 8:(i + 1) * 8], 'big') ^ _const_id, 8, 'big'
                )
            session_string_cipher = session_string_lenten[:353]
        key = md5(key1).digest() + key2
        crypt = pyaes.AESModeOfOperationCTR(key)
        session_string_encoded = crypt.decrypt(session_string_cipher)
        session_string = session_string_encoded.decode()
        client = TelegramClient(StringSession(session_string), api_id, api_hash, **client_args)
        client.parse_mode = "HTML"
        await client.start()
        current_sessions[_sess] = {"client": client, "expires_in": int(time()) + 60 * 60 * 3}
    client_id = f"client{_sess_id}"
    g.__setattr__(client_id, client)
    session['client_id'] = client_id
    return client_id


def new_cookies(ip: str, user_agent: str, sess_id: int) -> str:
    ip_part = md5(ip.encode()).hexdigest()[:11]
    user_agent_part = md5(user_agent.encode() + int.to_bytes(sess_id, 8, 'big')).hexdigest()[11:]
    ip_end_part = md5(md5(ip.encode()).digest()).hexdigest()[-6:]
    return ip_part + user_agent_part + ip_end_part


def encrypt_session_string(client: TelegramClient, key1: bytes, key2: bytes, is_const=False) -> Tuple[str, int]:
    session_string = StringSession.save(client.session)
    key = md5(key1).digest() + key2
    crypt = pyaes.AESModeOfOperationCTR(key)
    session_string_cipher = crypt.encrypt(session_string.encode())
    if is_const:
        session_string_cipher += b'\x00' * 7
        magic = int.from_bytes(session_string_cipher[:8], 'big') ^ 15279119701704967917
        session_string_salted = b''
        for i in range(len(session_string_cipher) // 8):
            session_string_salted += int.to_bytes(
                int.from_bytes(session_string_cipher[i * 8:(i + 1) * 8], 'big') ^ magic, 8, 'big'
            )
        session_string_cipher = session_string_salted
    else:
        magic = 0
    session_string_b64 = base64.urlsafe_b64encode(session_string_cipher)
    return session_string_b64.decode(), magic


def get_client_ip(headers, force_print=False) -> str:
    for x in ["X-Forwarded-For", "X-Real-Ip", "Remote-Addr"]:
        ips = headers.get(x)
        if ips:
            ips = ips.split(',')
        else:
            ips = []
        for ip in ips:
            if ip.strip() and not IpWorker.ip_spec_contains(ip.strip()):
                if force_print:
                    return ip.strip()
                ipnum = IpWorker.ip2num(ip.strip())
                for k, v in cidrs.items():
                    if v[0] <= ipnum <= v[1]:
                        return k
                try:
                    cidr = IpWorker.get_asn_cidr_by_ip(ip.strip())
                except Exception as e:
                    logging.warning(f"cidr for {ip.strip()} not found, okay - {e}")
                    cidr = ip.strip() + '/32'
                cidrs[cidr] = IpWorker.cidr_ip2num(cidr)
                logging.info(f"{cidr} - add to cidrs dict")
                return cidr
    return '' if not force_print else ips[0].strip()


def check_phone(phone: str):
    return (phone.startswith('+') and phone[1:].isnumeric()) \
           or phone.isnumeric()


def check_bot_token(bot_token: str):
    l = bot_token.split(':')
    return len(l) == 2 and l[0].isnumeric()


def get_title_or_name(entity,
                      print_self=True,
                      print_title=True,
                      print_short=False) -> str:
    res = ''
    if not print_self and getattr(entity, "is_self", False):
        return res
    if isinstance(entity, User):
        res = escape(entity.first_name) + (" " + escape(entity.last_name) if entity.last_name else "")
    elif not print_title:
        return res
    else:
        res = escape(entity.title)
    if print_short:
        return res[:10] + ("…" if len(res) > 10 else "")
    return res


def pack_xid(_id: int, _hash: int, is_user: bool) -> int:
    _sign = 0
    if _hash < 0:
        _hash *= -1
        _sign = 1
    return (_hash << 54) | ((_sign << 53) | ((int(is_user) << 52) | _id))


def unpack_xid(xid: int) -> TypeInputPeer:
    is_user = (xid >> 52) & 1
    _sign = (xid >> 53) & 1
    _id = xid & (2 ** 52 - 1)
    _hash = xid >> 54
    if _sign:
        _hash *= -1
    if _hash == -1488:
        return InputPeerChat(_id)
    if is_user:
        return InputPeerUser(_id, _hash)
    return InputPeerChannel(_id, _hash)


def xid2id(xid: int) -> int:
    return xid & (2 ** 52 - 1)


def xid2hash(xid: int) -> int:
    return xid >> 54


def render_emoji(html_in: str):
    answer = ''
    i = 0
    for _emoji in emoji.emoji_list(html_in):
        text = re.findall(r'[0-9a-f]+', ascii(_emoji['emoji']))
        text[:] = [x.lstrip("0") for x in text]
        if text[0].__len__() % 4:
            if text[0].__len__() == 1:
                text[0] = hex(ord(text[0])).replace('x', '0')
            elif text[0].__len__() == 2:
                text[0] = "00" + text[0]
        answer += html_in[i:_emoji['match_start']] + \
            f"<img src='{t}/emoji/{'-'.join(text)}.jpeg'> "
        i = _emoji['match_end']
    return answer + html_in[i:]


def fetch_emoji(filename: str):
    path = filename[:-5]
    resp = urlopen(f"https://web.telegram.org/z/img-apple-160/{path}.png")
    b = io.BytesIO(resp.read())
    b.seek(0)
    im = Image.open(b)
    if im.mode in ['P', 'PA', 'L', 'LA']:
        im.load()
        im_rgb = im.convert('RGBA')
    else:
        im_rgb = im
    background = Image.new("RGB", im_rgb.size, (255, 255, 255))
    background.paste(im_rgb, mask=im_rgb.split()[3])
    im_rgb = background
    im_rgb.thumbnail((24, 24))
    im_rgb.save(f'{emojipath}/{filename}', 'JPEG', quality=50)


# message's header generator
async def put_message_head(x, xid):
    res = ''
    user = await x.get_sender()
    date = x.date.astimezone(my_tz)
    if user and getattr(user, 'deleted', False):
        res += "<b><i>дЕЛЕТЕД аЦЦОУНТ</i></b><br>"
    else:
        res += f'<b>{get_title_or_name(user, print_self=False, print_title=False)}</b><br>'
    res += f'<i>{date.hour}:{(0 if date.minute < 10 else "")}{date.minute} {date.day}.{date.month}.{date.year}</i><p>'
    if x.is_reply:
        y = await x.get_reply_message()
        if not y:
            return res
        user = await y.get_sender()
        if user and getattr(user, 'deleted', False):
            resname = ""
        else:
            resname = get_title_or_name(user, print_short=True) if user else ''
        if y.raw_text:
            restext = f'<br><i>{escape(y.raw_text[:10])}</i>'
        else:
            restext = f'<br>NotTextMessage'
        res += f'<a href="{t}/{xid}?message_id={y.id}"><i>»{resname}</i>{restext}</p></a>'
    return res


# message's content generator
async def put_content(x: Message, client: TelegramClient, limited=None):
    res = ''
    if x.media.__class__ == MessageMediaPhoto:
        mediatype = x.media.photo
        im = None
        img = f'static/images/{mediatype.dc_id}_{mediatype.id}.jpeg'
        try:
            if not exists(img):
                await client.download_media(x, img)
                im = Image.open(img)
                im.thumbnail((128, 128))
                im.save(img, 'JPEG', quality=40)
            res += f'<img src="/{img}"/><p>'
        except Exception as e:
            logging.warning(f"corrupt image file - {e}")
            if im:
                im.close()
            if os.path.exists(img):
                os.remove(img)
    if x.media.__class__ == MessageMediaDocument:
        mediatype = x.media.document
        mime, ext = mediatype.mime_type.split('/')
        if mime == 'image':
            try:
                img = f'static/images/{mediatype.dc_id}_{mediatype.id}'
                if not exists(img + '.jpeg'):
                    await client.download_media(x, f'{img}.{ext}')
                    im = Image.open(f'{img}.{ext}')
                    im.verify()
                    if im.mode == 'RGBA':
                        im.load()
                        background = Image.new("RGB", im.size, (255, 255, 255))
                        background.paste(im, mask=im.split()[3])
                        im = background
                    im.thumbnail((102, 102))
                    im.save(img + '.jpeg', 'JPEG', quality=40)
                    im.close()
                res += f'<img src="/{img}.jpeg"/><p>'
            except Exception as e:
                logging.warning(f"corrupt image file - {e}")
        elif mime == 'audio' and ext == 'ogg':
            fileref = base64.b64encode(x.media.document.file_reference).decode('UTF-8')
            x.media.document.file_reference = '&'
            x.media.document.attributes[0].waveform = b''
            crypt = pyaes.AESModeOfOperationCTR(saltkey(aeskey))
            media64 = crypt.encrypt(str(x.media).encode())
            media64 = base64.b64encode(media64).decode('UTF-8')
            res += f'<form action="{t}/dl" method="post"><input type="hidden" name="media" value="{media64}" />' \
                   f'<input type="hidden" name="fileref" value="{fileref}" /><input type="submit" value="# ili.!.i|l ' \
                   f'{x.media.document.attributes[0].duration}s" /></form>'
    if x.message:
        if limited and x.fwd_from:
            raw = x.raw_text[:100] + '...'
        else:
            ent = []
            for y in x.entities or []:
                url = ''
                pattern = '/p?u='
                if isinstance(y, MessageEntityUrl):
                    url = x.get_entities_text(MessageEntityUrl)[0][1]
                    if not url.startswith("http://") and not url.startswith("https://"):
                        url = 'http://' + url
                    url = pattern + url
                elif isinstance(y, MessageEntityTextUrl):
                    url = pattern + y.url
                elif isinstance(y, MessageEntityMention):
                    url = pattern + "https://t.me/" + x.get_entities_text(MessageEntityMention)[0][1][1:]
                elif isinstance(y, MessageEntityMentionName):
                    try:
                        user = await client.get_entity(y.user_id)
                        xid = pack_xid(user.id, user.access_hash, True)
                    except Exception as e:
                        logging.warning(f"wrong entity for mention {y.user_id} - {e}")
                        xid = y.user_id
                    url = f"{t}/{xid}"
                if url:
                    ent.append(MessageEntityTextUrl(y.offset, y.length, url))
            x.entities = ent
            raw = x.text
        res += "<p>" + "<br>".join(raw.split(n)) + "</p>"
    return res


# salt aeskey for additional security
def saltkey(aes_key, prev=False):
    base = (int(time()) >> 10) - (1 if prev else 0)
    timestamp = base * 2 ** 10
    al = list(aes_key)
    ai = 0
    while timestamp > 0:
        ii = timestamp % 256
        timestamp //= 256
        al[ai] ^= ii
        ai += 1
    return bytes(al)


# for most angry search engine bots
def hello_everybot():
    useragent = request.headers.get('User-Agent')
    if 'Googlebot' in useragent:
        return True, temp.replace('%', 'Hi, Googlebot!')
    elif 'YandexBot' in useragent:
        return True, temp.replace('%', 'Hello, YandexBot!')
    return False, None
