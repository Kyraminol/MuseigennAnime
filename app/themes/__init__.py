import sys
from pathlib import Path
from re import sub


def get_themes():
    themes = {}
    if getattr(sys, "frozen", False):
        path = Path(sys.executable).parent / "app" / "themes"
    else:
        path = Path(__path__[0])
    folders = [theme for theme in path.iterdir() if theme.is_dir() and not theme.name.startswith("_")]
    for theme_folder in folders:
        theme_files = [x for x in theme_folder.glob("theme.py")]
        if len(theme_files) < 1:
            continue
        theme_file = theme_files[0]
        theme_dict = {}
        with theme_file.open() as theme:
            for line in theme.readlines():
                line = sub(r"[\n\r]", "", line).split(" = ")
                if not len(line) == 2:
                    continue
                k = str(line[0])
                v = str(line[1])
                if not k.startswith("_") and k.isupper() and v.startswith('"') and v.endswith('"'):
                    theme_dict[k] = v[1:-1]
                theme_dict["__theme_folder__"] = theme_folder.parts[-1]
        themes[theme_folder.parts[-1]] = theme_dict
    return themes
