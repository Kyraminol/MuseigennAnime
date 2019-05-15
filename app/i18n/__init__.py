# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from .i18n import Translator

if getattr(sys, "frozen", False):
    traslator = Translator(Path(sys.executable).parent / "app" / "i18n")
else:
    traslator = Translator(Path(__path__[0]))
translate = traslator.translate
accepted_languages = traslator.accepted_languages
