import json
from urllib.parse import urlparse, urlencode, parse_qs
from .. import task
from ..profile import AuthError
from ..http import HTTP
from . import Judge, Testcase


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


class AOJClient(HTTP, Judge, Testcase):
    CREDENTIAL: [
        ("id", "User ID", False),
        ("password", "Password", True)
    ]

    ENV: (
'''
C,GCC,5.1.1,Linux,x86_64,C,C11
''')

    def http_response(self, request, response):
        response = super().http_response(request, response)
        if response.getcode() == 400:
            error = response.body[0]
            # 1102: INVALID_REFRESH_TOKEN_ERROR
            # 1401: USER_NOT_FOUND_ERROR
            if error["id"] in (1102,1401):
                raise AuthError(error['message'])
        return response

    def pid(self, o):
        return parse_qs(o.query)["id"][0]

    def testcase(self, pid, serial):
        response = self.open(f"https://judgedat.u-aizu.ac.jp/testcases/{pid}/{serial}")
        data = response.body
        if not data["in"].endswith(LIMITATION) and not data["out"].endswith(LIMITATION):
            return data

    def testcases(self, pid, writer):
        response = self.open(f"https://judgedat.u-aizu.ac.jp/testcases/{pid}/header")
        headers = response.body["headers"]
        assert len(headers) > 1 or (headers[0]["inputSize"] + headers[0]["outputSize"] > 0)

        for case in headers:
            data = self.testcase(pid, case["serial"])
            if data is None:
                continue
            for f, s in zip(writer.add(case["name"]), (data["in"], data["out"])):
                with f:
                    f.write(s.encode())

        writer.save()

    def login(self):
        self.raw_open(
            "https://judgeapi.u-aizu.ac.jp/session",
            self.credential,
            {'Content-Type': self.JSON})

    def submit(self, pid, env, code):
        response = self.open(
            "https://judgeapi.u-aizu.ac.jp/submissions",
            { "sourceCode": code.decode(),
              "language": env,
              "problemId": pid },
            {'Content-Type': self.JSON})

        token = json.loads(response.body)['token']
        response = self.open("https://judgeapi.u-aizu.ac.jp/submission_records/recent")
        data = response.body

        for item in data:
            if item["token"] == token:
                return "http://judge.u-aizu.ac.jp/onlinejudge/review.jsp?" + urlencode({"rid": item["judgeId"]}) + "#2"
        assert False

    def status(self, token):
        token = parse_qs(urlparse(token).query)["rid"][0]

        response = self.open(f"https://judgeapi.u-aizu.ac.jp/verdicts/{token}")
        data = response.body["submissionRecord"]
        status = data["status"]
        message = STATUS[status]

        if status in (5, 9):
            return None, message
        elif status == 4:
            return (True,
                    message,
                    {'memory': data['memory'],
                     'runtime': data['cpuTime'],
                     'codesize': data['codeSize']})
        assert status >= 0
        return False, message
