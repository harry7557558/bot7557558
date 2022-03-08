# keep the bot up on repl.it

from flask import Flask
from threading import Thread

app = Flask('')


@app.route('/')
def home():
    return """<center><h1>Hello, World!</h1></center><hr><center>bot7557558/0.0.0.0</center>"""


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()
