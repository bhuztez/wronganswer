from base64 import b64encode
from urllib.parse import urlparse, urlencode, quote_from_bytes, parse_qsl
import logging
import json
from ..profile import AuthError
from ..http import HTTP
from ..image import display
from . import Agent

logger = logging.getLogger(__package__)

ONLINE_JUDGES = {
    'judge.u-aizu.ac.jp': 'Aizu',
    'poj.org': 'POJ',
}


class VjudgeAgent(HTTP, Agent):
    CREDENTIAL: [
        ("username", "Username or Email", False),
        ("password", "Password", True)
    ]

    def __init__(self, profile, netloc):
        super().__init__(profile, netloc)
        self._captcha_required = False

    def http_request(self, request):
        request.add_header('Referer', f'https://{self.netloc}/')
        request.add_header('X-Requested-With', 'XMLHttpRequest')
        if self._captcha_required == True and request.get_header('Content-type', None) == self.URLENCODE:
            qs = parse_qsl(request.data)
            captcha = self.captcha()
            request.data = urlencode(qs + [("captcha", captcha)]).encode()
        return super().http_request(request)

    def http_response(self, request, response):
        response = super().http_response(request, response)
        data = response.body
        if isinstance(data, dict) and "error" in data:
            if data.get("captcha", False):
                self._captcha_required = True
                assert False, "Captcha required"
            else:
                raise AuthError(data["error"])
        return response

    def login(self):
        response = self.raw_open(
            "/user/login",
            self.credential,
            {'Content-Type': self.URLENCODE})
        body = response.body
        if body != "success":
            raise AuthError(body)

    def _submit(self, oj, pid, env, code):
        response = self.open(
            "/problem/submit",
            { "oj": ONLINE_JUDGES[oj],
              "probNum": pid,
              "language": env,
              "share": 0,
              "source": b64encode(quote_from_bytes(code).encode()),
              "captcha": "" },
            {'Content-Type': self.URLENCODE})
        self._captcha_required = False
        return response.body

    def captcha(self):
        response = self.open("/util/serverTime", method="POST")
        server_time = response.body
        response = self.open(f"/util/captcha?{response.body}")
        display(response.body)
        return input("Captcha: ")

    def submit(self, oj, pid, env, code):
        data = self._submit(oj, pid, env, code)
        if "error" not in data:
            runId = data["runId"]
            return f"https://{self.netloc}/solution/{runId}"
        assert data.get("captcha", False)
        assert False, "Captcha required"

    def status(self, oj, token):
        token = urlparse(token).path.rstrip("/").rsplit("/",1)[1]

        response = self.open(
            f"/solution/data/{token}",
            { "showCode": "false" },
            {'Content-Type': self.URLENCODE})

        data = response.body
        if data["processing"]:
            return None, data["status"]
        if data["statusType"] != 0:
            return False, data["status"]
        data.setdefault("memory", "N/A")
        data.setdefault("runtime", "N/A")
        data.setdefault("length", "N/A")
        return (True,
                data["status"],
                {'memory': data['memory'],
                 'runtime': data['runtime'],
                 'codesize': data['length']})
