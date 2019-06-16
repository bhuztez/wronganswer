from io import StringIO
from http.cookiejar import LWPCookieJar
from urllib.request import build_opener, Request, HTTPCookieProcessor, BaseHandler, AbstractHTTPHandler
from urllib.parse import urlencode, urlparse, urlunparse
from http.client import HTTPResponse
import json
from email.message import Message, _parseparam
from html.parser import HTMLParser
from xml.etree.ElementTree import TreeBuilder, XML
from miasma.utils import lazy_property
import logging
from . import task
from .profile import AuthError, Persistable

logger = logging.getLogger(__package__)

class Form(Message):

    def __init__(self):
        super().__init__(self)
        self.add_header('Content-Type', 'multipart/form-data')
        self._payload = []

    def _write_headers(self, _generator):
        # skip headers
        pass


class Field(Message):

    def __init__(self,name,text):
        super().__init__(self)
        self.add_header('Content-Disposition','form-data',name=name,charset="utf-8")
        self.set_payload(text,None)


def parse_content_type(content_type):
    content_type, *params = _parseparam(content_type)
    main_type, subtype = content_type.split("/")
    params = dict(param.split("=",1) for param in params)
    return content_type, main_type, subtype, params

def normalize_url(scheme, netloc, url):
    o = urlparse(url)
    return urlunparse(o._replace(scheme=o.scheme or scheme, netloc=o.netloc or netloc))

def request(scheme, netloc, url, data=None, headers=None, method=None):
    if isinstance(url, Request):
        url.fullurl = normalize_url(scheme, netloc, url.fullurl)
        url.method = url.get_method()
        return url
    url = normalize_url(scheme, netloc, url)
    headers = headers or {}
    content_type = headers.get('Content-Type', None)
    if content_type is None:
        if data is not None:
            url += '?' + urlencode(data)
        return Request(url, headers=headers, method=method or "GET")
    content_type, main_type, subtype, params = parse_content_type(content_type)
    charset = params.get("charset", "ascii")
    if not isinstance(data, bytes):
        if subtype == 'json':
            data = json.dumps(data).encode(charset)
        elif content_type == 'application/x-www-form-urlencoded':
            data = urlencode(data).encode(charset)
        elif content_type == 'multipart/form-data':
            form = Form()
            for name,value in data.items():
                if isinstance(value,bytes):
                    form.attach(Field(name,value))
                else:
                    form.attach(Field(name,str(value).encode('utf-8')))
            data = form.as_string().encode(charset)
        else:
            assert False, f"unknown Content-Type {content_type}"
    return Request(url, data, headers, method=method or "POST")


class HTMLParser(HTMLParser):

    def __init__(self, target):
        super().__init__()
        self.target = target

    def handle_starttag(self, tag, attrs):
        self.target.start(tag, dict(attrs))

    def handle_endtag(self, tag):
        self.target.end(tag)

    def handle_data(self, data):
        self.target.data(data)

    def close(self):
        return self.target.close()


class Response(HTTPResponse):

    @lazy_property
    def body(self):
        data = self.read()
        content_type = self.info().get('Content-Type', None)
        if content_type is not None:
            content_type, main_type, subtype, params = parse_content_type(content_type)
            charset = params.get("charset", "ascii")
            data = data.decode(charset)
            if subtype == 'json':
                data = json.loads(data)
            elif subtype == 'html':
                data = XML(data, parser=HTMLParser(TreeBuilder()))

        return data

USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1"


class HTTP(BaseHandler, Persistable):
    scheme = 'https'
    JSON = 'application/json; charset=UTF-8'
    URLENCODE = 'application/x-www-form-urlencoded; charset=UTF-8'
    FORMDATA = 'multipart/form-data'

    def __init__(self, profile, netloc):
        self.profile = profile
        self.netloc = netloc
        self._cookiejar = LWPCookieJar()
        self._auth_required = False
        self.credential = None
        opener = build_opener()
        for h in (HTTPCookieProcessor(self._cookiejar),
                  self):
            opener.add_handler(h)
        opener.addheaders = [('User-Agent', USER_AGENT)]

    def set_http_debuglevel(self, level):
        for handler in self.parent.handlers:
            if isinstance(handler, AbstractHTTPHandler):
                handler.set_http_debuglevel(level)

    def http_request(self, request):
        return request

    def https_request(self, request):
        return self.http_request(request)

    def http_response(self, request, response):
        response.__class__ = Response
        return response

    def https_response(self, request, response):
        return self.http_response(request, response)

    def __getstate__(self):
        state = {"cookie": self._cookiejar.as_lwp_str()}
        if self.credential:
            state["credential"] = self.credential
        return json.dumps(state)

    def __setstate__(self, state):
        state = json.loads(state)
        self._cookiejar._really_load(StringIO("#LWP-Cookies-2.0\n" + state["cookie"]), "cookies.txt",True,True)
        self.credential = state.get("credential", None)

    def get_cookie(self, name):
        for cookie in self._cookiejar:
            if cookie.name == name:
                return cookie.value

    def _do_open(self, request):
        try:
            self.set_http_debuglevel(self.profile.debug)
            return self.parent.open(request)
        except AuthError:
            request.remove_header("Cookie")
            raise

    @task("HTTP {request.method} {request.full_url}", retry=True)
    def _open(self, request):
        if self._auth_required:
            self.profile.auth(self)
            self._auth_required = False
        try:
            return self._do_open(request)
        except AuthError as e:
            self._auth_required = True
            assert False, str(e)

    @task("HTTP {request.method} {request.full_url}", retry=True)
    def _raw_open(self, request):
        return self._do_open(request)

    def open(self, url, data=None, headers=None, method=None):
        return self._open(request(self.scheme, self.netloc, url, data, headers, method))

    def raw_open(self, url, data=None, headers=None, method=None):
        return self._raw_open(request(self.scheme, self.netloc, url, data, headers, method))
