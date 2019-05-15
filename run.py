import logging
import sys
from app import create_app, socketio, translate, default_locale
from argparse import ArgumentParser
from webbrowser import open
from pathlib import Path
from werkzeug import serving
from gevent.subprocess import Popen

frozen = getattr(sys, "frozen", False)
fmt = logging.Formatter("%(asctime)s - "
                        "[%(processName)s] "
                        "[%(threadName)s] "
                        "[%(name)s] - "
                        "[%(lineno)d] %(funcName)s() - "
                        "[%(levelname)s] %(message)s")
file_logger = logging.FileHandler("debug.log", "w")
file_logger.setLevel(logging.DEBUG)
file_logger.setFormatter(fmt)
stream_logger = logging.StreamHandler()
stream_logger.setLevel(logging.INFO)
stream_logger.setFormatter(fmt)
logging.basicConfig(level=logging.DEBUG, handlers=[stream_logger, file_logger])


def start_app(console):
    app = create_app(frozen=frozen, console=console)
    host = app.config.get("HOST", "127.0.0.1")
    port = app.config.get("PORT", 5000)
    use_reloader = app.config.get("USE_RELOADER")
    if not use_reloader and not app.config.get("DEBUG") and app.config.get("OPEN_AFTER_RUN", True):
        open("http://localhost:{port}".format(port=port))
    socketio.run(app, host=host, port=port, use_reloader=use_reloader)


def build_app(console):
    def rm_dir(path_to_rm):
        for x in path_to_rm.iterdir():
            if x.is_file():
                x.unlink()
            else:
                rm_dir(x)
        path_to_rm.rmdir()
    specfile = "default.spec"
    if console:
        specfile = "console.spec"
    path = Path(".").absolute()
    spec = path / "app" / "utils" / "spec" / specfile
    tmp = path / "tmp"
    p = Popen("pyinstaller {spec} --distpath {path} --workpath {tmp}".format(spec=spec, path=path, tmp=tmp))
    p.wait()
    rm_dir(Path("./tmp"))
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 0 and sys.argv[-1] == "start":
        start_app(False)
        sys.exit(0)
    parser = ArgumentParser(description=translate("ma_args_description", default_locale), add_help=False)
    parser.add_argument("-c", "--console", help=translate("ma_args_console", default_locale), action="store_true")
    parser.add_argument("-b", "--build", help=translate("ma_args_build", default_locale), action="store_true")
    parser.add_argument("-h", "--help", help=translate("ma_args_help", default_locale), action="help")
    args = parser.parse_args()
    if args.build:
        build_app(args.console)
    if not args.console and not frozen:
        logging.info(translate("launching_no_console", default_locale))
        try:
            Popen(["pythonw", __file__, "start"])
        except FileNotFoundError:
            Popen(["python", __file__, "start"])
    else:
        if not serving.is_running_from_reloader():
            logging.info(translate("launching_console", default_locale))
        start_app(args.console)
