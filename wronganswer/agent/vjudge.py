from base64 import b64encode
from urllib.parse import urlparse, quote_from_bytes
import logging
import json
from ..profile import AuthError
from ..http import HTTP
from ..image import display
from . import Agent

logger = logging.getLogger(__package__)

ONLINE_JUDGES = {
    'judge.u-aizu.ac.jp': 'Aizu',
}


class VjudgeAgent(HTTP, Agent):

    def http_request(self, request):
        request.add_header('Referer', f'https://{self.netloc}/')
        request.add_header('X-Requested-With', 'XMLHttpRequest')
        return super().http_request(request)

    async def login(self, credential: [
            ("username", "Username or Email", False),
            ("password", "Password", True)
    ]):
        if credential is not None:
            self._credential = credential
        if self._credential is None:
            raise AuthError("Credential not provided")

        response = await self.raw_open(
            f"https://{self.netloc}/user/login",
            self._credential,
            {'Content-Type': self.URLENCODE})
        body = response.read()
        print(body)
        if body != b"success":
            raise AuthError(body)

    async def _submit(self, oj, pid, env, code, captcha):
        response = await self.open(
            f"https://{self.netloc}/problem/submit",
            { "oj": ONLINE_JUDGES[oj],
              "probNum": pid,
              "language": env,
              "share": 0,
              "source": b64encode(quote_from_bytes(code).encode()),
              "captcha": captcha,
            },
            {'Content-Type': self.URLENCODE})
        data = json.loads(response.read())
        if "error" in data:
            if not data.get("captcha", False):
                raise AuthError(data["error"])
        return data

    async def captcha(self):
        response = await self.open(f"https://{self.netloc}/util/serverTime", method="POST")
        server_time = response.read()
        response = await self.open(f"https://{self.netloc}/util/captcha?" + server_time.decode())
        display(response.read())
        return input("Captcha: ")

    async def submit(self, oj, pid, env, code):
        captcha = ""
        while True:
            try:
                data = await self._submit(oj, pid, env, code, captcha)
                if "error" not in data:
                    runId = data["runId"]
                    return f"https://{self.netloc}/solution/{runId}"
                assert data.get("captcha", False)
                captcha = await self.captcha()
            except AuthError as e:
                logger.warning("Login required, %s", e)
                await self.profile.auth(self.netloc, self)

    async def status(self, oj, token):
        token = urlparse(token).path.rstrip("/").rsplit("/",1)[1]

        response = await self.open(
            f"https://{self.netloc}/solution/data/{token}",
            { "showCode": "false" },
            {'Content-Type': self.URLENCODE})

        data = json.loads(response.read())
        if data["processing"]:
            return None, data["status"]
        if data["statusType"] != 0:
            return False, data["status"]
        data.setdefault("memory", "N/A")
        data.setdefault("runtime", "N/A")
        data.setdefault("length", "N/A")
        return True, data["status"], 'Memory: {memory}, Time: {runtime}, Length: {length}'.format(**data)
