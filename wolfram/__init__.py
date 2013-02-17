from flask import Flask

app = Flask(__name__)
app.config.from_object('wolfram.config')
app.jinja_env.globals.update(zip=zip)
app.jinja_env.globals.update(bool=bool)

import wolfram.views
