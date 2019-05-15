# -*- coding: utf-8 -*-
import logging
from locale import getdefaultlocale
from re import sub, match
from json import loads as json_loads
from importlib.util import spec_from_file_location, module_from_spec
from flask import Blueprint, render_template, request, current_app, jsonify, abort, Response
from flask_socketio import SocketIO, emit
from gevent import spawn_later, sleep
from gevent.queue import Empty
from .utils.download_manager import DownloadManager
from .utils.language_accept import LanguageAccept
from .i18n import translate, accepted_languages
from .themes import get_themes
from .modules import modules

LOGGER = logging.getLogger(__name__)
DEFAULT_LOCALE = LanguageAccept([(getdefaultlocale()[0], 0.02), ("en", 0.01)])
main_view = Blueprint("main_view", __name__)
socketio = SocketIO(async_mode="gevent")
DOWNLOAD_MANAGER = DownloadManager(socketio, LOGGER)
HANDLERS = {}
THEMES = get_themes()
DOWNLOADS = {"queue": [],
             "downloads": {}}


@main_view.route("/")
def index():
    current_app.app_context()
    handlers_config = current_app.config.get("HANDLERS", {})
    if isinstance(handlers_config, str):
        handlers_config = json_loads(handlers_config)
        current_app.config["HANDLERS"] = handlers_config
    return render_template("index.html",
                           translate=translate,
                           lang=get_lang(),
                           config=current_app.config,
                           theme=get_theme(),
                           themes=THEMES,
                           handlers=HANDLERS,
                           handlers_config=handlers_config)


@main_view.route("/player")
def player():
    anime_id = request.args.get("anime_id")
    handler_id = request.args.get("handler_id")
    if not anime_id or not handler_id:
        abort(400)
    handler = HANDLERS.get(int(handler_id))
    anime = handler.get_anime(int(anime_id))
    return render_template("player.html",
                           anime=anime,
                           translate=translate,
                           lang=get_lang(),
                           config=current_app.config,
                           theme=get_theme())


@main_view.route("/settings", methods=["POST"])
def settings():
    for key, value in request.form.items():
        if key not in current_app.config["CONFIG_NOT_SAVE"]:
            current_app.config[key] = value
    file = current_app.config["APP_PATH"] / "config.py"
    with file.open(mode="w") as f:
        for key, value in current_app.config.items():
            if (not isinstance(value, str) and not isinstance(value, bool) and not isinstance(value, int)) or not value:
                continue
            if key in current_app.config["CONFIG_NOT_SAVE"]:
                continue
            if isinstance(value, str):
                value = '"' + sub(r"\\", "\\\\\\\\", value) + '"'
            if key == "HANDLERS":
                value = json_loads(value[1:-1])
            f.writelines("{key} = {value}\n".format(key=key, value=value))
    return ""


@main_view.route("/api/v1/anime/<int:handler_id>")
def api_anime_list(handler_id):
    result = {}
    handler = HANDLERS[handler_id]
    anime_list = handler.get_list()
    anime_list.sort(key=lambda a: a.name)
    for anime in anime_list:
        char = anime.name[:1].lower()
        if match(r"[0-9a-z]", char):
            if match(r"[0-9]", char):
                char = "0-9"
        else:
            char = "#"
        if char in result:
            result[char].append(anime)
        else:
            result[char] = [anime]
    return jsonify(result)


@main_view.route("/api/v1/anime/<int:handler_id>/<int:anime_id>")
def api_anime_info(handler_id, anime_id):
    handler = HANDLERS.get(handler_id)
    anime = handler.get_anime(anime_id)
    info = anime.get_info()
    result = "ok"
    message = ""
    if not info:
        result = "error"
    return jsonify({"result": result, "message": message, "data": info})


@main_view.route("/api/v1/anime/<int:handler_id>/<int:anime_id>/<int:season_id>/<int:episode_id>")
def api_get_episode(handler_id, anime_id, season_id, episode_id):
    handler = HANDLERS.get(handler_id)
    anime = handler.get_anime(anime_id)
    season = anime.get_season(season_id)
    episode = season.get_episode(episode_id)
    return jsonify(episode.get_info())


@main_view.route("/api/v1/downloads", methods=["POST"])
def api_downloads():
    episodes = json_loads(request.form.get("episodes", []))
    stream = request.form.get("stream_download")
    if stream == "true":
        stream = True
    else:
        stream = False
    if not episodes:
        abort(400)
    downloads_dict = {}
    downloads_list = []
    for episode in episodes:
        print(episode)
        handler_id = episode["handler_id"]
        anime_id = episode["anime_id"]
        season_id = episode["season_id"]
        episode_id = episode["episode_id"]
        handler = downloads_dict.get(handler_id, {})
        anime = handler.get(anime_id, {})
        season = anime.get(season_id, [])
        if episode_id not in season:
            season.append(episode_id)
        anime[season_id] = season
        handler[anime_id] = anime
        downloads_dict[handler_id] = handler
    n = 0
    for handler_id, anime_dict in downloads_dict.items():
        handler = HANDLERS.get(int(handler_id))
        if not handler:
            continue
        for anime_id, seasons_dict in anime_dict.items():
            anime = handler.get_anime(int(anime_id))
            if not anime:
                continue
            for season_id, episodes in seasons_dict.items():
                season = anime.get_season(int(season_id))
                if not season:
                    continue
                for episode_id in episodes:
                    episode = season.get_episode(int(episode_id))
                    if not episode:
                        continue
                    downloads_list.append(episode)
                    n += 1
    DOWNLOAD_MANAGER.queue_add(downloads_list,
                               get_config("DOWNLOAD_PATH"),
                               max_downloads=get_config("DOWNLOAD_MANAGER_MAX_DOWNLOADS", 2),
                               stream=stream)
    data = translate("download_episodes_queued", get_lang()).format(n=n)
    return jsonify({"result": "ok", "message": "", "data": data})


@main_view.route("/api/v1/download/<download_key>")
def download_serve(download_key):
    def response_yield(stream):
        while True:
            try:
                yield stream.queue.get(block=False)
            except Empty:
                if stream.finished and stream.queue.empty():
                    break
                sleep(0.05)
    dm_stream, status = DOWNLOAD_MANAGER.get_stream(download_key)
    if not dm_stream:
        abort(404)
    info = status["info"]
    filename = "{} - {} - {}.{}".format(info["anime_name_sane"], info["episode_n"], info["episode_title"], info["ext"])
    return Response(response_yield(dm_stream),
                    mimetype="application/octet-stream",
                    headers={"Content-Disposition": 'attachment; filename="{}"'.format(filename)})


@main_view.route("/api/v1/anime/download/<int:handler_id>/<int:anime_id>")
def api_anime_download(handler_id, anime_id):
    result = []
    handler = HANDLERS.get(handler_id)
    anime = handler.get_anime(anime_id)
    seasons = anime.get_seasons()
    for season in seasons:
        episodes = [episode.get_info() for episode in season.get_episodes()]
        result.append({"season_id": season.id, "season_name": season.name, "episodes": episodes})
    return jsonify({"result": "ok", "message": "", "data": result})


@main_view.route("/api/v1/themes")
def api_get_themes():
    THEMES.clear()
    THEMES.update(get_themes())
    return jsonify({"data": THEMES, "result": "ok", "message": ""})


@main_view.route("/api/v1/shutdown", methods=["POST"])
def shutdown():
    spawn_later(2, socketio.stop)
    return "Shutting down."


@socketio.on("connect", namespace="/downloads")
def socketio_downloads_connected():
    if not DOWNLOAD_MANAGER.is_downloading:
        emit("status", DOWNLOAD_MANAGER.history, namespace="/downloads")


@socketio.on("ACK", namespace="/downloads")
def socketio_downloads_ack():
    DOWNLOAD_MANAGER.ack()


@socketio.on("cancel", namespace="/downloads")
def socketio_downloads_cancel(msg):
    if "paths" in msg:
        for path in msg["paths"]:
            DOWNLOAD_MANAGER.cancel(path)
    return


@socketio.on("clean", namespace="/downloads")
def socketio_downloads_clean():
    DOWNLOAD_MANAGER.clean()


def get_lang():
    request_languages = LanguageAccept(request.accept_languages + DEFAULT_LOCALE)
    return request_languages.best_match(accepted_languages)


def get_config(attr, default=None):
    return current_app.config.get(attr, default)


def get_theme():
    theme_config = get_config("THEME")
    if theme_config in THEMES:
        return THEMES[theme_config]
    if len(THEMES) == 0:
        return {}
    if "default_dark" in THEMES:
        return THEMES["default_dark"]
    if "default_light" in THEMES:
        return THEMES["default_light"]
    random_theme = THEMES.popitem()
    if random_theme:
        THEMES.update(random_theme)
        return random_theme[1]
    return {}


def init_modules():
    basename = __name__.split(".")[0]
    for i, module_path in enumerate(modules):
        spec = spec_from_file_location(".".join((basename, "modules", module_path.name[:3])), str(module_path))
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        handler = module.Handler(i + 1)
        HANDLERS[handler.id] = handler


init_modules()
