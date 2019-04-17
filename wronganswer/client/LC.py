import json
from urllib.parse import urlparse
from time import sleep
from ..profile import AuthError
from ..http import HTTP
from . import Client


class LeetcodeClient(HTTP, Client):

    def http_request(self, request):
        request.add_header('Referer', f'https://{self.netloc}/')
        request.add_header('X-Requested-With', 'XMLHttpRequest')
        if request.get_header('Content-type') == self.JSON:
            request.add_header("X-CSRFToken", self.get_cookie("csrftoken"))
        return super().http_request(request)

    def http_response(self, request, response):
        if response.getcode() == 403:
            raise AuthError()
        if response.getcode() == 429:
            sleep(10)
        return response

    async def pid(self, o):
        return o.path.strip("/").split("/",2)[1]

    async def login(self, credential: [
            ("login", "Username or E-mail", False),
            ("password", "Password", True)]):
        if credential is not None:
            self._credential = credential
        if self._credential is None:
            raise AuthError("Credential not provided")

        data = {"csrfmiddlewaretoken": await self.get_csrftoken()}
        data.update(self._credential)

        await self.raw_open(
            f"https://{self.netloc}/accounts/login/",
            data,
            {'Content-Type': self.URLENCODE})

    async def get_csrftoken(self):
        if self.get_cookie("csrftoken") is None:
            await self.raw_open(f"https://{self.netloc}/")
        return self.get_cookie("csrftoken")


    async def submit(self, pid, env, code):
        '''
        c,GCC,6.3,Linux,x86_64,C,C11
        '''
        await self.get_csrftoken()
        response = await self.open(
            f"https://{self.netloc}/graphql",
            { "operationName": "questionData",
              "query": "query questionData($titleSlug: String!) { question(titleSlug: $titleSlug) { questionId } }",
              "variables": {
                  "titleSlug": pid
              }
            },
            {"Content-Type": self.JSON})
        questionId = json.loads(response.read())["data"]["question"]["questionId"]

        response = await self.open(
            f"https://{self.netloc}/problems/{pid}/submit/",
            { "typed_code": code.decode(),
              "question_id": questionId,
              "lang": env },
            {"Content-Type": self.JSON})
        submission_id = json.loads(response.read())["submission_id"]
        return f"https://{self.netloc}/submissions/detail/{submission_id}/"

    async def status(self, token):
        token = urlparse(token).path.rstrip("/").rsplit("/", 1)[1]
        response = await self.open(f"https://{self.netloc}/submissions/detail/{token}/check/")

        data = json.loads(response.read())
        state = data["state"]

        if state != "SUCCESS":
            return None, state

        msg = data["status_msg"]
        code = data["status_code"]
        if code == 10:
            memory = data["status_memory"]
            runtime = data["status_runtime"]
            return True, msg, f"Memory: {memory}, Time: {runtime}"

        error = "full_" + "_".join(s.lower() for s in msg.split())
        if error in data:
            return False, data[error]

        return False, msg

    async def snippet(self, pid, env):
        await self.get_csrftoken()
        response = await self.open(
            f"https://{self.netloc}/graphql",
            { "operationName": "questionData",
              "query": "query questionData($titleSlug: String!) { question(titleSlug: $titleSlug) { codeSnippets { langSlug code } } }",
              "variables": {
                  "titleSlug": pid
              }
            },
            {"Content-Type": self.JSON})

        for s in json.loads(response.read())["data"]["question"]["codeSnippets"]:
            if s['langSlug'] == env:
                return s['code']

    async def prologue(self, pid):
        snippet = await self.snippet(pid, 'c')
        snippet = snippet.rstrip()
        assert snippet.endswith("}")
        snippet = snippet[:-1].rstrip()
        assert snippet.endswith("{")
        snippet = snippet[:-1].rstrip() + ";\n"
        return snippet.encode()
