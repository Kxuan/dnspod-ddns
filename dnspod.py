import requests
import json

class DnsPodMethodProxy:
    def __init__(self, dnspod, class_name, method_name):
        self.dnspod = dnspod
        self.class_name = class_name
        self.method_name = method_name

    def __call__(self, *args, **kwargs):
        return self.dnspod.do_request("{}.{}".format(self.class_name, self.method_name), **kwargs)

class DnsPodClassProxy:
    def __init__(self, dnspod, name):
        self.dnspod = dnspod
        self.class_name = name

    def __getattr__(self, item):
        return DnsPodMethodProxy(self.dnspod, self.class_name, item)

class DnsPodError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return "{}: {}".format(self.code, self.message)

class DnsPod:
    def __init__(self, token):
        self.ua = "kXuan dnspod/0.0.0 (kxuanobj@gmail.com)"
        self.generic_args = {
            "login_token": token,
            "format": "json",
            "lang": "en",
            "error_on_empty": "no"
        }

    def __getattr__(self, item):
        return DnsPodClassProxy(self, item)

    def do_request(self, name, **kwargs):
        r = requests.post("https://dnsapi.cn/" + name,
                          data={**kwargs, **self.generic_args},
                          headers={
                              "User-Agent": self.ua
                          })
        if r.status_code != 200:
            raise requests.HTTPError(r.reason)
        o = json.loads(r.text)
        if int(o["status"]["code"]) != 1:
            raise DnsPodError(o["status"]["code"],o["status"]["message"])
        return o
