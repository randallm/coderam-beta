from flask import Flask

app = Flask(__name__)
app.config.from_object('wolfram.config')

import wolfram.views
