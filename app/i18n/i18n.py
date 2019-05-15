# -*- coding: utf-8 -*-
from gettext import translation


def _(text):
    return text


class Translator:
    def __init__(self, path):
        self._path = path
        langs = set([x.parts[-1] for x in self._path.iterdir() if x.is_dir() and not x.name.startswith('_')])
        if "en" not in langs:
            langs.add("en")
        self.accepted_languages = langs

    def translate(self, attr, lang="en"):
        text = getattr(self, "_" + attr, None)
        if text:
            translator = translation("webapp", languages=[lang], localedir=str(self._path), fallback=True)
            return translator.gettext(text)
        return attr

    _watch = _("Watch")
    _settings = _("Settings")
    _loading = _("Loading...")
    _error_loading_list = _("An error as occourred while loading the anime list")
    _error_loading_info = _("An error as occourred while loading the anime info")
    _error_loading_info_not_available = _("Anime not available from this source")
    _lights = _("Lights")
    _download = _("Download")
    _episode = _("Episode")
    _previous = _("Previous")
    _next = _("Next")
    _close = _("Close")
    _error_downloading = _("An error as occourred while downloading")
    _hls_not_supported = _("HLS player is not supported by this browser")
    _error_loading_episode = _("An error as occourred while loading the anime episode")
    _autoplaying = _("Autoplaying next episode...")
    _click_anywhere_cancel = _("Click anywhere to cancel")
    _cancel = _("Cancel")
    _save = _("Save")
    _settings_anime_subpath = _("Create anime sub-folder")
    _settings_season_subpath = _("Create season sub-folder")
    _theme_by = _('Theme "{theme_name}" by {theme_author}')
    _theme = _("Theme")
    _interface = _("Interface")
    _advanced = _("Advanced")
    _settings_advanced_text = _("Don't touch anything from below if you aren't sure of what you're doing.")
    _port = _("Port")
    _download_folder = _("Download folder")
    _settings_theme_no_name = _("No Name")
    _settings_theme_no_author = _("No Author")
    _download_episodes_queued = _("Episodes added to the download queue: {n}")
    _download_manager = _("Download Manager")
    _download_manager_no_downloads = _("No downloads")
    _download_manager_downloads = _("Downloading: {0} - Completed: {1} - Queued: {2}")
    _download_manager_max_downloads = _("Max parallel downloads")
    _clean = _("Clean")
    _cancel_all = _("Cancel All")
    _finished = _("Finished")
    _downloading = _("Downloading")
    _eta = _("ETA")
    _anime = _("Anime")
    _episode_title = _("Episode title")
    _status = _("Status")
    _progress = _("Progress")
    _speed = _("Speed")
    _queued = _("Queued")
    _cancelled = _("Cancelled")
    _error_empty_list = _("Error: Anime list is empty please add or enable some modules!")
    _exit = _("Exit")
    _open = _("Open")
    _ma_args_description = _("Options for launching MuseigennAnime, default will run with UI")
    _ma_args_console = _("Run or build with console instead of UI")
    _ma_args_build = _("Build frozen executable and exit")
    _ma_args_help = _("Show this help message and exit")
    _launching_no_console = _("Launching MuseigennAnime without console...")
    _launching_console = _("Launching MuseigennAnime with console...")
    _shutdown_app = _("Shutdown MuseigennAnime")
    _confirm = _("Confirm")
    _shutdown_modal_confirm = _("Do you really want to shutdown MuseigennAnime?")
    _search = _("Search")
    _copy_address = _("Copy Address")
    _open_list = _("Open list")
    _search_current_module = _("Search current module only")
    _search_all_modules = _("Search all modules")
    _settings_advanced_switch = _("Show advanced settings")
    _interface_listen_all = _("Listen all interfaces")
    _interface_listen_custom = _("Listen on custom interface")
    _modules = _("Modules")
    _modules_select = _("Enable/Disable Modules")
    _select_module = _("Select a module from above or below")
    _download_stream_device = _("Download directly to this device")
