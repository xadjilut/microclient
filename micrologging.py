import base64
import datetime
import logging
from html import escape

from quart import request
from quart_rate_limiter import rate_limit

from helper import aeskey
from values import temp

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename="microlog"
)
logging.getLogger('telethon.network.mtprotosender').setLevel(logging.WARNING)


@rate_limit(3, datetime.timedelta(seconds=3))
def microlog(secret_part: str):
    if secret_part != base64.urlsafe_b64encode(aeskey).decode()[:7]:
        return temp.replace(
            '%', "2022-07-15 14:88:42,228 - hypercorn.error - INFO - Running on http://0.0.0.0:8090 (CTRL + C to quit)")
    with open("microlog", 'r') as f:
        lines = f.readlines()
    offset = request.args.get("offset", "0")
    if offset.isnumeric():
        offset = int(offset)
    else:
        offset = 0
    offset_link = f'<a href="/microlog/{secret_part}?offset={offset + 1}">{escape(">>>")}</a>'
    text = f'{offset_link}<br>'
    i = 0
    for x in lines[::-1]:
        i += len(x)
        if i < offset * 4444:
            continue
        if i > (offset + 1) * 4444:
            text += offset_link
            break
        text += f"<p>{escape(x)}</p>"
    return temp.replace('%', text)
