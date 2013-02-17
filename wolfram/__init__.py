from flask import Flask

app = Flask(__name__)
app.config.from_object('wolfram.config')
app.jinja_env.globals.update(zip=zip)

import wolfram.views
