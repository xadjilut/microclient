import logging


def log(string):
    with open('microlog', 'a') as f:
        f.write(string + '\n')


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename="microlog"
)
logging.getLogger('telethon.network.mtprotosender').setLevel(logging.WARNING)
