import json
from urllib.parse import urlparse, urlencode, parse_qs
from .. import task
from ..profile import AuthError
from ..http import HTTP
from . import Client


LIMITATION = "..... (terminated because of the limitation)\n"

STATUS = {
    -1: "Judge Not Available",
    0: "Compile Error",
    1: "Wrong Answer",
    2: "Time Limit Exceeded",
    3: "Memory Limit Exceeded",
    4: "Accepted",
    5: "Waiting Judge",
    6: "Output Limit Exceeded",
    7: "Runtime Error",
    8: "Presentation Error",
    9: "Running",
}


class AOJClient(HTTP, Client):

    def http_response(self, request, response):
        if response.getcode() == 400:
            body = response.read()
            error = json.loads(body)[0]
            # 1102: INVALID_REFRESH_TOKEN_ERROR
            # 1401: USER_NOT_FOUND_ERROR
            if error["id"] in (1102,1401):
                raise AuthError(error['message'])
        return response

    async def pid(self, o):
        return parse_qs(o.query)["id"][0]

    async def testcase(self, pid, serial):
        response = await self.open(f"https://judgedat.u-aizu.ac.jp/testcases/{pid}/{serial}")
        data = json.loads(response.read().decode("utf-8"))
        if not data["in"].endswith(LIMITATION) and not data["out"].endswith(LIMITATION):
            return data

    async def testcases(self, pid, writer):
        response = await self.open(f"https://judgedat.u-aizu.ac.jp/testcases/{pid}/header")
        headers = json.loads(response.read().decode())["headers"]
        assert len(headers) > 1 or (headers[0]["inputSize"] + headers[0]["outputSize"] > 0)

        for case in headers:
            data = await self.testcase(pid, case["serial"])
            if data is None:
                continue
            for f, s in zip(writer.add(case["name"]), (data["in"], data["out"])):
                with f:
                    f.write(s.encode())

        writer.save()

    async def login(self, credential: [
            ("id", "User ID", False),
            ("password", "Password", True)]):
        if credential is not None:
            self._credential = credential
        if self._credential is None:
            raise AuthError("Credential not provided")

        await self.raw_open(
            "https://judgeapi.u-aizu.ac.jp/session",
            self._credential,
            {'Content-Type': self.JSON})

    async def submit(self, pid, env, code):
        '''
        C,GCC,5.1.1,Linux,x86_64,C,C11
        '''
        response = await self.open(
            "https://judgeapi.u-aizu.ac.jp/submissions",
            { "sourceCode": code.decode(),
              "language": env,
              "problemId": pid },
            {'Content-Type': self.JSON})

        token = json.loads(response.read())['token']
        response = await self.open("https://judgeapi.u-aizu.ac.jp/submission_records/recent")
        data = json.loads(response.read())

        for item in data:
            if item["token"] == token:
                return "http://judge.u-aizu.ac.jp/onlinejudge/review.jsp?" + urlencode({"rid": item["judgeId"]}) + "#2"
        assert False

    async def status(self, token):
        token = parse_qs(urlparse(token).query)["rid"][0]

        response = await self.open(f"https://judgeapi.u-aizu.ac.jp/verdicts/{token}")
        data = json.loads(response.read())["submissionRecord"]
        status = data["status"]
        message = STATUS[status]

        if status in (5, 9):
            return None, message
        elif status == 4:
            return True, message, 'Memory: {memory}, Time: {cpuTime}, Length: {codeSize}'.format(**data)

        assert status >= 0
        return False, message
