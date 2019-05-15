import logging
from webbrowser import open
from gevent import sleep
from netifaces import interfaces, ifaddresses, AF_INET
from wx import Icon, CallLater, MenuItem, EVT_MENU, Menu, App, Frame, CallAfter, TheClipboard, TextDataObject
from wx.adv import TaskBarIcon, EVT_TASKBAR_LEFT_DOWN


class WxApp(App):
    def __init__(self, icon_path, translate, lang, app, socketio, **kwargs):
        self.logging = logging.getLogger(__name__)
        self.icon_path = icon_path
        self.translate = translate
        self.lang = lang
        self.app = app
        self.socketio = socketio
        self.kwargs = kwargs
        self.frame = None
        self.taskbaricon = None
        super().__init__()

    @staticmethod
    def create_menu_item(menu, label, func):
        item = MenuItem(menu, -1, label)
        menu.Bind(EVT_MENU, func, id=item.GetId())
        menu.Append(item)
        return item

    def create_popup_menu(self):
        menu = Menu()
        self.create_menu_item(menu, self.translate("open", self.lang), self.left_click)
        menu.AppendSeparator()
        self.create_menu_item(menu, self.translate("copy_address", self.lang), self.copy_address)
        menu.AppendSeparator()
        self.create_menu_item(menu, self.translate("exit", self.lang), self.on_exit)
        return menu

    def OnInit(self):
        self.frame = Frame(None)
        self.SetTopWindow(self.frame)
        self.taskbaricon = self._TaskBarIcon(self.frame, self.icon_path, "MuseigennAnime", self.left_click)
        self.taskbaricon.CreatePopupMenu = self.create_popup_menu
        self.sleep()
        return True

    def copy_address(self, _):
        host = None
        for iface in interfaces():
            addresses = ifaddresses(iface).get(AF_INET)
            if addresses:
                for address in addresses:
                    if address["addr"].startswith("192.168."):
                        host = address["addr"]
        if TheClipboard.Open():
            text_obj = TextDataObject("http://{host}:{port}".format(host=host, port=self.app.config.get("PORT", 5000)))
            TheClipboard.SetData(text_obj)
            TheClipboard.Close()

    def left_click(self, _):
        open("http://localhost:{port}".format(port=self.app.config.get("PORT", 5000)))

    def on_exit(self, _):
        CallAfter(self.taskbaricon.Destroy)
        CallAfter(self.socketio.stop)
        self.frame.Close()

    def sleep(self):
        CallLater(10, self.sleep)
        sleep(0.01)

    class _TaskBarIcon(TaskBarIcon):
        def __init__(self, frame, icon_path, tooltip, left_click):
            self.frame = frame
            self.left_click = left_click
            super().__init__()
            self.SetIcon(Icon(icon_path), tooltip)
            self.Bind(EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

        def on_left_down(self, *args):
            return self.left_click(*args)
