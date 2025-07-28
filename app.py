from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Subject, Chapter


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'BK-3QBD15JF8ZuaG5F6HAqMNEHIcHaqQ2Mdz5nvd6kZA4TigbRfGv99-unD7Smo8fOU'

db.init_app(app)
app.app_context().push()

with app.app_context():
    db.create_all()

from controllers.routes import *


if __name__ == "__main__":
    app.run(debug=True)