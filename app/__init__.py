# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
from flask import Flask
from gevent import spawn
from .views import main_view, socketio, translate, accepted_languages, DEFAULT_LOCALE
from .utils.json_encoder import MAJSONEncoder
try:
    from .wxapp import WxApp
    console_override = False
except ImportError:
    console_override = True

default_locale = DEFAULT_LOCALE.best_match(accepted_languages)


def create_app(frozen=False, console=True):
    if console_override:
        console = True
    if not console:
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")
        sys.stdin = open(os.devnull, "w")
    if frozen:
        app_path = Path(sys.executable).parent / "app"
    else:
        app_path = Path(__path__[0])
    app = Flask(__name__, template_folder=app_path / "templates", static_folder=app_path / "static")
    app.json_encoder = MAJSONEncoder
    config = app_path / "config.py"
    config.touch(exist_ok=True)
    app.config.from_pyfile(str(config))
    if not app.config.get("DOWNLOAD_PATH"):
        app.config.update(DOWNLOAD_PATH=Path.home() / "Downloads" / "MuseigennAnime")
    app.config.update(APP_PATH=app_path, APP_FROZEN=frozen,
                      CONFIG_NOT_SAVE=("APP_PATH", "APP_FROZEN"))
    if frozen or not console:
        app.config["DEBUG"] = False
        app.config["USE_RELOADER"] = False
    if not console:
        wx = WxApp(str(app_path / "static" / "img" / "logo.png"),
                   translate,
                   default_locale,
                   app,
                   socketio)
        spawn(wx.MainLoop)
    app.register_blueprint(main_view)
    socketio.init_app(app)
    return app
