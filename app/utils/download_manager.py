from pathlib import Path
from io import BytesIO
from contextlib import redirect_stdout
from time import time
from youtube_dl import YoutubeDL
from gevent.pool import Pool
from gevent import sleep, getcurrent
from gevent.queue import Queue
from json import loads, JSONDecodeError
from uuid import uuid4


class DownloadManager:
    def __init__(self, socketio, logger):
        self._socketio = socketio
        self._logger = logger
        self._queue = []
        self._history = {}
        self._gthreads = {}
        self._streams = {}
        self._downloading = False
        self._is_ack = False
        self._last = None
        self._ydl_opts = {"hls_prefer_native": True,
                          "progress_hooks": [self._hook],
                          "logger": self._logger}

    def queue_add(self, episodes, base_path, anime_subdir=True, season_subdir=True, max_downloads=2, stream=False):
        for episode in episodes:
            info = {"anime_name": episode.season.anime.name,
                    "anime_name_sane": self._sanitize(episode.season.anime.name),
                    "url": episode.get_info().get("video_url")}
            episode_name = "S{s}E{e}".format(s=episode.season.id,
                                             e=episode.get_info().get("episode_number", episode.id))
            info["episode_n"] = episode_name
            episode_title = self._sanitize(episode.get_info().get("episode_title", ""))
            if episode_title:
                info["episode_title"] = episode_title
                episode_name = episode_name + " - " + episode_title
            if not stream:
                path = Path(base_path)
                if anime_subdir:
                    path /= self._sanitize(episode.season.anime.name)
                if season_subdir:
                    path /= self._sanitize(episode.season.name)
                path.mkdir(parents=True, exist_ok=True)
                key = str(path / episode_name)
            else:
                key = "?" + str(uuid4())
                max_downloads = 1
            info["key"] = key
            self._history[key] = {"status": {"status": "queued"},
                                  "info": info}
            self._queue.append(info)
        self._process_queue(int(max_downloads))

    def cancel(self, path):
        for item in self._queue:
            if item[0] == path:
                self._queue.remove(item)
        if path in self._gthreads:
            gthread = self._gthreads[path]
            gthread.kill()
            self._gthreads.pop(path)
        self._history[path]["status"] = {"status": "cancelled"}

    def clean(self):
        for path, values in self._history.copy().items():
            status = values["status"]["status"]
            if not status == "queued" and not status == "downloading":
                self._history.pop(path)
        self._socketio.emit("status", self._history, namespace="/downloads")

    def _process_queue(self, pool_n):
        if not self._downloading:
            self._downloading = True
            gpool = Pool(pool_n)
            while self._queue:
                info = self._queue.pop(0)
                key = info["key"]
                gthread = gpool.spawn(self._download, info)
                self._gthreads[key] = gthread
                if key.startswith("?"):
                    self._socketio.emit("serve", key[1:], namespace="/download")
            self._downloading = False

    def _download(self, info):
        key = info["key"]
        url = info["url"]
        if key.startswith("?"):
            self._streams[key] = CustomBytesIO()
            json_logger = JSONLogger()
            with YoutubeDL(self._ydl_opts) as ydl:
                ydl.params.update(logger=json_logger, forcejson=True, simulate=True)
                ydl.download([url])
            self._history[key]["info"]["ext"] = json_logger.json["ext"]
            with redirect_stdout(self._streams[key]):
                with YoutubeDL(self._ydl_opts) as ydl:
                    ydl.params.update(outtmpl="-")
                    ydl.download([url])
        else:
            with YoutubeDL(self._ydl_opts) as ydl:
                ydl.params.update(outtmpl=key + ".%(ext)s")
                ydl.download([url])

    @staticmethod
    def _sanitize(string):
        keep = (" ", ".", "_", "'", "!", "-")
        return "".join(char for char in string if char.isalnum() or char in keep).strip()

    def _hook(self, status):
        if status["filename"] == "-":
            key = str(getcurrent().args[0]["key"])
            if status["status"] == "finished":
                self._streams[key].set_finished()
            if not self._streams[key].retrieved:
                self._socketio.emit("serve", key[1:], namespace="/download")
        else:
            path = Path(status["filename"])
            key = str(path)[:-len(path.suffix)]
        self._history[key]["status"] = status
        if self._is_ack or status["status"] == "finished" or not self._last or (time() - self._last) > 10:
            self._is_ack = False
            self._last = time()
            self._socketio.emit("status", self._history, namespace="/downloads")
        sleep(0.1)

    def ack(self):
        self._is_ack = True

    def get_stream(self, key):
        stream = self._streams.get("?" + key)
        if stream:
            stream.set_retrieved()
        return stream, self._history.get("?" + key)

    def _get_history(self):
        return self._history.copy()

    def _get_downloading(self):
        return self._downloading

    history = property(_get_history)
    is_downloading = property(_get_downloading)


class CustomBytesIO(BytesIO):
    def __init__(self, *args, **kwargs):
        super(BytesIO, self).__init__(*args, **kwargs)
        self.queue = Queue()
        self._finished = False
        self._retrieved = False

    def fileno(self):
        return 1

    def set_retrieved(self):
        self._retrieved = True

    def set_finished(self):
        self._finished = True

    def _get_retrieved(self):
        return self._retrieved

    def _get_finished(self):
        return self._finished

    def write(self, *args, **kwargs):
        self.queue.put(args[0])
        self.flush()

    finished = property(_get_finished)
    retrieved = property(_get_retrieved)


class JSONLogger(object):
    def __init__(self):
        self._json = None

    def debug(self, msg):
        try:
            self._json = loads(msg)
        except JSONDecodeError:
            pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

    def _get_json(self):
        return self._json

    json = property(_get_json)
