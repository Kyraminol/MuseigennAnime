# -*- coding: utf-8 -*-
from ..models.handler import BaseHandler, Anime, Season, Episode
from requests import Session
from urllib.parse import urlparse, urlunparse
from gevent import sleep
from re import sub


class Handler(BaseHandler):
    def __init__(self, handler_id):
        super().__init__(handler_id, handler_name="VVVVID")
        self._s = Session()
        self._s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:64.0) Gecko/20100101 Firefox/64.0"
        self.__conn_id = ""
        self.__channels = []
        self.url = "https://www.vvvvid.it"
        self._list = []
        self._table = {}

    def get_list(self, force_update=False):
        if not self._list or force_update:
            channel_name = "A - Z"
            channel = [channel for channel in self._get_channels() if channel.get("name") == channel_name][0]
            url_last = "{base_url}/vvvvid/ondemand/anime/channel/{channel_id}/last".format(base_url=self.url,
                                                                                           channel_id=channel["id"])
            url = "{base_url}/vvvvid/ondemand/anime/channel/{channel_id}".format(base_url=self.url,
                                                                                 channel_id=channel["id"])
            result = []
            anime_id = 1
            for channel_filter in channel["filter"]:
                r_last = self._request(url_last, params={"filter": channel_filter, "conn_id": self._conn_id})
                r = self._request(url, params={"filter": channel_filter, "conn_id": self._conn_id})
                anime_list = [*r_last.get("data", []), *r.get("data", [])]
                for anime in anime_list:
                    show_id = anime["show_id"]
                    a = Anime(self,
                              anime.get("title"),
                              anime_id,
                              show_id=show_id,
                              info_url="{base_url}/vvvvid/ondemand/{show_id}/info/".format(base_url=self.url,
                                                                                           show_id=show_id),
                              seasons_url="{base_url}/vvvvid/ondemand/{show_id}/seasons/".format(base_url=self.url,
                                                                                                 show_id=show_id))
                    self._table[anime_id] = a
                    result.append(a)
                    anime_id += 1
                sleep()
            self._list = result
        return self._list

    def get_anime(self, anime_id):
        if not self._table:
            self.get_list(force_update=True)
        return self._table.get(anime_id)

    def get_info(self, anime):
        result = {}
        seasons = []
        info = self._request(anime.get_data("info_url"), params={"conn_id": self._conn_id})
        seasons_info = self._request(anime.get_data("seasons_url"), params={"conn_id": self._conn_id})
        info_data = info.get("data")
        if info_data:
            result["trama"] = info_data.get("description", "Trama non ancora inserita.")
            more_info = {"anno": info_data.get("date_published", "Non specificato")}
            additional_infos = info_data.get("additional_info", "").split("|")
            for line in additional_infos:
                additional_info = line.strip().split(":")
                more_info[additional_info[0].strip()] = additional_info[1].strip() or ""
            result["altre_informazioni"] = more_info
        seasons_data = seasons_info.get("data")
        if seasons_data:
            result["episodi"] = {}
            episode_id = 1
            for season_id, season in enumerate(seasons_data):
                name = season.get("name", "Non specificato")
                season_vvvvid_id = season["season_id"]
                season_obj = Season(anime, season_id, name, season_vvvvid_id=season_vvvvid_id)
                episodes = []
                for episode in season.get("episodes", []):
                    episode = Episode(season_obj,
                                      episode_id,
                                      episode_vvvvid_id=episode["id"],
                                      episode_n=episode["number"],
                                      episode_url="{base_url}/vvvvid/ondemand/{anime_id}/season/{season_id}".format(
                                          base_url=self.url,
                                          anime_id=anime.get_data("show_id"),
                                          season_id=season_vvvvid_id),
                                      availability_date=episode.get("availability_date", None))
                    episodes.append(episode)
                    episode_id += 1
                season_obj.set_data("episodes", episodes)
                seasons.append(season_obj)
                result["episodi"][name] = len(episodes)
        anime.set_data("seasons", seasons)
        return result

    def get_seasons(self, anime):
        seasons = anime.get_data("seasons")
        if not seasons:
            self.get_info(anime)
            seasons = anime.get_data("seasons")
        return seasons

    def get_episodes(self, anime, season):
        episodes = season.get_data("episodes")
        if not episodes:
            self.get_info(anime)
            episodes = anime.get_data("episodes")
        return episodes

    def get_episode_info(self, anime, season, episode):
        raw_data = season.get_data("raw_data")
        if not raw_data:
            url = episode.get_data("episode_url")
            if not url:
                self.get_info(anime)
                url = episode.get_data("episode_url")
            r = self._request(url, params={"conn_id": self._conn_id})
            raw_data = r.get("data", [])
            season.set_data("raw_data", raw_data)
        info = [x for x in raw_data if x.get("id") == episode.get_data("episode_vvvvid_id")]
        if len(info) < 1:
            availability_date = episode.get_data("availability_date")
            if availability_date:
                return {"availability_date": availability_date}
            return {}
        info = info[0]
        video_url = urlparse(self._decrypt_url(info.get("embed_info")))
        video_url = urlunparse(("https",) + video_url[1:])
        video_url_sd = info.get("embed_info_sd")
        if video_url_sd:
            video_url_sd = urlunparse(("https",) + urlparse(self._decrypt_url(video_url_sd))[1:])
        video_type = info.get("video_type", "video/hls")
        if video_type in ("video/rcs", "video/kenc"):
            video_url = sub(r"https?://([^/]+)/z/", r"https://\1/i/", video_url).replace("/manifest.f4m", "/master.m3u8")
            if video_type == "video/kenc":
                kenc = self._request("https://www.vvvvid.it/kenc", params={"action": "kt",
                                                                           "conn_id": self._conn_id,
                                                                           "url": video_url}) or {}
                kenc_message = kenc["message"]
                if kenc_message:
                    video_url += "?" + self._decrypt_url(kenc_message)
                    video_type = "video/hls"
        result = {"episode_id": episode.id,
                  "video_url": video_url,
                  "video_url_sd": video_url_sd,
                  "video_type": video_type,
                  "source_type": info.get("source_type"),
                  "episode_title": info.get("title"),
                  "episode_number": info.get("number", episode.id)}
        return result

    def _request(self, url, post=False, max_retries=3, **kwargs):
        r = None
        for i in range(0, max_retries):
            if post:
                r = self._s.post(url, **kwargs).json()
            else:
                r = self._s.get(url, **kwargs).json()
            if r.get("result") == "error" and "forbidden" in r.get("message"):
                if i == max_retries - 1:
                    raise Exception("Too many token failures")
                else:
                    self._get_conn_id(force_update=True)
            else:
                break
        return r

    def _get_conn_id(self, force_update=False):
        if not self.__conn_id or force_update:
            data = {"action": "login",
                    "email": "",
                    "facebookParams": "",
                    "flash": False,
                    "hls": True,
                    "isIframe": False,
                    "mobile": False,
                    "password": ""}
            r = self._s.post("{base_url}/user/login".format(base_url=self.url), data=data)
            json = r.json()
            self.__conn_id = json.get("data", {}).get("conn_id", "")
        return self.__conn_id

    def _get_channels(self):
        if not self.__channels:
            url = "{base_url}/vvvvid/ondemand/anime/channels".format(base_url=self.url)
            r = self._request(url, params={"conn_id": self._conn_id})
            self.__channels = r.get("data", [])
        return self.__channels

    @staticmethod
    def _decrypt_url(url):
        if not url:
            return None
        g = "MNOPIJKL89+/4567UVWXQRSTEFGHABCDcdefYZabstuvopqr0123wxyzklmnghij"

        def f(m):
            pp = []
            o = 0
            b = False
            m_len = len(m)
            while not b and o < m_len:
                n = m[o] << 2
                o += 1
                k = -1
                j = -1
                if o < m_len:
                    n += m[o] >> 4
                    o += 1
                    if o < m_len:
                        k = (m[o - 1] << 4) & 255
                        k += m[o] >> 2
                        o += 1
                        if o < m_len:
                            j = (m[o - 1] << 6) & 255
                            j += m[o]
                            o += 1
                        else:
                            b = True
                    else:
                        b = True
                else:
                    b = True
                pp.append(n)
                if k != -1:
                    pp.append(k)
                if j != -1:
                    pp.append(j)
            return pp

        c = []
        for e in url:
            c.append(g.index(e))
        c_len = len(c)
        for e in range(c_len * 2 - 1, -1, -1):
            a = c[e % c_len] ^ c[(e + 1) % c_len]
            c[e % c_len] = a
        c = f(c)
        d = ''
        for e in c:
            d += chr(e)
        return d

    _conn_id = property(_get_conn_id)
