import re
from urllib.parse import urlparse, parse_qs, urlunparse
from ..models.handler import BaseHandler, Anime, Season, Episode
from requests import Session
from bs4 import BeautifulSoup


class Handler(BaseHandler):
    def __init__(self, handler_id):
        super().__init__(handler_id, handler_name="AnimeForce")
        self._s = Session()
        self.__conn_id = ""
        self.__channels = []
        self.url = "https://ww1.animeforce.org"
        self._list = []
        self._table = {}
        self._re_title = re.compile(r"( sub)?( ita)?( download)?( & )?(streaming)?", re.I)
        self._re_number = re.compile(r"\d+")
        self._re_dl404 = re.compile(r"d=404")
        self._re_dlonsite = re.compile(r"animeforce")
        self._re_dlonyt = re.compile(r"youtube")
        self._re_dlnotavail = re.compile(r"(nodownload|nostream)")
        self._re_dlpage = re.compile(r"(ds0?1?6?\.php\?file=.+|wp-content/.+|dl\.php\?file=.+)")
        self._re_dspage = re.compile(r"/ds0?1?6?\.php")

    def get_list(self, force_update=False):
        if not self._list or force_update:
            anime_list = []
            r = self._s.get(self.url + "/lista-anime/")
            soup = BeautifulSoup(r.content, "lxml")
            content = soup.find("div", attrs={"class": "the-content"})
            if not content:
                return anime_list
            attrs = {"href": True}
            anime_id = 1
            for ul in content.find_all("ul"):
                for anchor in ul.find_all("a", attrs=attrs):
                    anime = Anime(self,
                                  re.sub(self._re_title, "", anchor.text).strip(),
                                  anime_id,
                                  anime_url=anchor["href"])
                    anime_list.append(anime)
                    self._table[anime_id] = anime
                    anime_id += 1
            self._list = anime_list
        return self._list

    def get_anime(self, anime_id):
        if not self._table:
            self.get_list(force_update=True)
        return self._table.get(anime_id)

    def get_info(self, anime):
        info = {}
        url = anime.get_data("anime_url")
        r = self._s.get(url)
        soup = BeautifulSoup(r.content, "lxml")
        for encrypted_email in soup.select('a.__cf_email__'):
            enc = bytes.fromhex(encrypted_email['data-cfemail'])
            decrypted = bytes([c ^ enc[0] for c in enc[1:]]).decode('utf8')
            encrypted_email.replace_with(decrypted)
        div = soup.find("div", {"class": "the-content"})
        if not div:
            return info
        tables = div.find_all("tbody")
        if not len(tables) > 0:
            return info
        for tr in tables[0].find_all("tr"):
            tds = tr.find_all("td")
            if not tds:
                continue
            info[tds[0].text] = tds[1].text
        if not len(tables) > 1:
            info["_available"] = False
            return info
        episodes = []
        season = Season(anime, 1, "Episodi")
        attrs = {"href": True}
        for table in tables[1:]:
            for episode_id, tr in enumerate(table.find_all("tr")):
                tds = tr.find_all("td")
                if not tds:
                    continue
                url = re.sub(r"www\.animeforce", "ww1.animeforce", tds[1].find("a", attrs=attrs)["href"])
                img = tds[1].find("img")["src"]
                if re.search(self._re_dlnotavail, img):
                    continue
                episode = Episode(season, episode_id, url=url, episode_title=tds[0].text)
                episodes.append(episode)
        season.set_data("episodes", episodes)
        anime.set_data("seasons", [season])
        return info

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

    def _parse_qs(self, url, qs):
        if "://" not in qs["file"][0]:
            qs["file"][0] = "http://" + qs["file"][0]
        video_url = urlparse(qs["file"][0], "http", allow_fragments=False)
        if "." not in video_url[1]:
            easydeath = "/easydeath/16ds.php"
            if re.search(r"ds\.php", url.geturl()):
                easydeath = "/easydeath/ds.php"
            r = self._s.get(urlunparse(url[0:2] + (easydeath,) + url[3:]), allow_redirects=False)
            if r.status_code == 302 or r.status_code == 301:
                if re.search(self._re_dl404, r.headers["location"]):
                    return None
                video_url = parse_qs(urlparse(r.headers["location"])[4])["file"][0]
                if "://" not in video_url:
                    video_url = "http://" + video_url
                video_url = urlparse(video_url, "http", allow_fragments=False)
        return video_url.geturl()

    def _parse_animeforce_link(self, url):
        url = urlparse(url, "https")
        if not url[1]:
            url = urlparse(urlunparse(url[0:1] + ("ww1.animeforce.org",) + url[2:]))
        if url[4]:
            qs = parse_qs(url[4])
            if "file" in qs:
                return 1, self._parse_qs(url, qs)
        if url[2] and re.search(self._re_dspage, url[2]):
            url = urlparse(re.sub(re.escape(url[2]), "/ds16.php", url.geturl()))
        return 0, url

    def get_episode_info(self, anime, season, episode):
        info = {"episode_title": episode.get_data("episode_title"),
                "episode_id": episode.id}
        result, url = self._parse_animeforce_link(episode.get_data("url"))
        if result:
            info["video_url"] = url
            return info
        r = self._s.get(url.geturl(), allow_redirects=False)
        if (r.status_code == 301 or r.status_code == 302) and re.search(self._re_dlonsite, r.headers["location"]):
            result, url = self._parse_animeforce_link(r.headers["location"])
            if result:
                info["video_url"] = url
                return info
        r = self._s.get(url.geturl())
        if re.search(self._re_dl404, r.url):
            return info
        if not re.search(self._re_dlonsite, r.url):
            if re.search(self._re_dlonyt, r.url):
                info["video_url"] = r.url
            return info
        r_url = urlparse(r.url)
        if r_url[4]:
            qs = parse_qs(r_url[4])
            if "file" in qs:
                info["video_url"] = self._parse_qs(url, qs)
                return info
        soup = BeautifulSoup(r.content, "lxml")
        link = soup.find("source", attrs={"src": True})
        if link:
            info["video_url"] = link["src"]
            return info
        scripts = soup.find_all("script", attrs={"type": "text/javascript"})
        for script in scripts:
            rex = re.search(r"file: \"([^\"]+)\"", script.text)
            if rex:
                link = rex.group(1)
        if link:
            info["video_url"] = link
            return info
