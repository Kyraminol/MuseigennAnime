# -*- coding: utf-8 -*-


class BaseHandler:
    def __init__(self, handler_id, handler_name):
        self.__id = handler_id
        self.__name = handler_name
        self.__active = True

    def __get_id(self):
        return self.__id

    def __get_name(self):
        return self.__name

    def __get_active(self):
        return self.__active

    def __set_active(self, status):
        if status is True or status is False:
            self.__active = status

    def __repr__(self):
        return '<Handler object name="{name}" id="{id}">'.format(name=self.name, id=self.id)

    id = property(__get_id)
    name = property(__get_name)
    active = property(__get_active, __set_active)


class Anime:
    def __init__(self, handler, anime_name, anime_id, **kwargs):
        self.__handler = handler
        self.__name = anime_name
        self.__id = anime_id
        self._data = kwargs
        self._info = {}
        self._seasons = []
        self._table = {}

    def get_info(self, force_update=False):
        if not self._info or force_update:
            self._info = self.handler.get_info(self)
        return self._info

    def get_seasons(self, force_update=False):
        if not self._seasons or force_update:
            self._seasons = self.handler.get_seasons(self)
            for season in self._seasons:
                self._table[season.id] = season
        return self._seasons

    def get_episodes(self, season):
        return self.handler.get_episodes(self, season)

    def set_data(self, data_name, data):
        self._data[data_name] = data

    def get_data(self, data_name, default=None):
        return self._data.get(data_name, default)

    def get_season(self, season_id):
        if not self._table:
            self.get_seasons(force_update=True)
        return self._table.get(season_id)

    def get_episode_info(self, season, episode):
        return self.handler.get_episode_info(self, season, episode)

    def __get_handler(self):
        return self.__handler

    def __get_id(self):
        return self.__id

    def __get_name(self):
        return self.__name

    def __repr__(self):
        return '<Anime object handler_id="{handler_id}" id="{anime_id}" name="{anime_name}" seasons={seasons}>'.format(
            handler_id=self.handler.id, anime_id=self.id, anime_name=self.name, seasons=len(self._seasons))

    handler = property(__get_handler)
    id = property(__get_id)
    name = property(__get_name)


class Season:
    def __init__(self, anime, season_id, season_name, **kwargs):
        self.__anime = anime
        self.__name = season_name
        self.__id = season_id
        self._data = kwargs
        self._info = {}
        self._episodes = []
        self._table = {}

    def get_episodes(self, force_update=False):
        if not self._episodes or force_update:
            self._episodes = self.anime.get_episodes(self)
            for episode in self._episodes:
                self._table[episode.id] = episode
        return self._episodes

    def set_data(self, data_name, data):
        self._data[data_name] = data

    def get_data(self, data_name, default=None):
        return self._data.get(data_name, default)

    def get_episode(self, episode_id):
        if not self._table:
            self.get_episodes(force_update=True)
        return self._table.get(episode_id)

    def get_episode_info(self, episode):
        return self.anime.get_episode_info(self, episode)

    def __get_anime(self):
        return self.__anime

    def __get_id(self):
        return self.__id

    def __get_name(self):
        return self.__name

    def __repr__(self):
        return '<Season object anime_id="{anime_id}" id="{season_id}" name="{season_name}" episodes={episodes}>'.format(
            anime_id=self.anime.id, season_id=self.id, season_name=self.name, episodes=len(self._episodes))

    anime = property(__get_anime)
    id = property(__get_id)
    name = property(__get_name)


class Episode:
    def __init__(self, season, episode_id, **kwargs):
        self.__season = season
        self.__id = episode_id
        self._data = kwargs
        self._info = {}

    def get_info(self, force_update=False):
        if not self._info or force_update:
            self._info = self.season.get_episode_info(self)
        return self._info

    def set_data(self, data_name, data):
        self._data[data_name] = data

    def get_data(self, data_name, default=None):
        return self._data.get(data_name, default)

    def __get_season(self):
        return self.__season

    def __get_id(self):
        return self.__id

    def __repr__(self):
        return '<Episode object season_id="{season_id}" id="{episode_id}" info_loaded={info_loaded}>'.format(
            season_id=self.season.id, episode_id=self.id, info_loaded=bool(self._info))

    season = property(__get_season)
    id = property(__get_id)
