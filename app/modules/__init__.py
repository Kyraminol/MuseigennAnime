# -*- coding: utf-8 -*-
import sys as __sys
from pathlib import Path as __Path

if getattr(__sys, "frozen", False):
    __path = __Path(__sys.executable).parent / "app" / "modules"
else:
    __path = __Path(__path__[0])
modules = [module
           for module in __path.glob("*.py")
           if module.is_file() and not module.name.startswith("_") and not module.name.endswith("__init__.py")]
