from re import compile
from werkzeug.datastructures import Accept

_locale_delim_re = compile(r"[_-]")


class LanguageAccept(Accept):
    def _value_matches(self, value, item):
        def _normalize(language):
            return _locale_delim_re.split(language.lower())
        return item == "*" or _normalize(value) == _normalize(item) or _normalize(value)[0] == _normalize(item)[0]
