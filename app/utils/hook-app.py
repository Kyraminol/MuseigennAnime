from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules("engineio")
hiddenimports += collect_submodules("requests")
hiddenimports += collect_submodules("bs4")
