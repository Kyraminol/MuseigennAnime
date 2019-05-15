from flask.json import JSONEncoder
from ..models.handler import Anime


class MAJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Anime):
            return obj.name, str(obj.id), str(obj.handler.id), obj.handler.name
        return JSONEncoder.default(self, obj)
