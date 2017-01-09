#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import flask

from models import db
from data import Consts
from models import logger
from api import api

def create_app():
    logger.info("[::|::]=- create_app({name}) -=[::|::]".format(name=__name__))

    app = flask.Flask("app")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data/prebot.db"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.register_blueprint(api)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    logger.info("Firin up FbBot using verify token [{verify_token}].".format(verify_token=Consts.VERIFY_TOKEN))
    app = create_app()
    app.run(debug=True)