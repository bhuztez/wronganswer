import json
from urllib.parse import urlparse
from time import sleep
from ..profile import AuthError
from ..http import HTTP
from . import Judge


class LeetcodeClient(HTTP, Judge):
    CREDENTIAL: [
        ("login", "Username or E-mail", False),
        ("password", "Password", True)]

    ENV: (
'''
cpp,GCC,8.2,Linux,x86_64,C++,C++17
java,OpenJDK,1.8.0,Linux,x86_64,Java,Java 8
python,CPython,2.7.12,Linux,x86_64,Python2,Python 2.7
python3,CPython,3.6.7,Linux,x86_64,Python3,Python 3.6
c,GCC,6.3,Linux,x86_64,C,C11
csharp,Mono,5.18.0,Linux,x86_64,C#,C# 7
javascript,Node.js,10.15.0,Linux,x86_64,ECMAScript,ES6
ruby,Ruby,2.4.5,Linux,x86_64,Ruby,Ruby 2.4
swift,Swift,5.0.1,Linux,x86_64,Swift,Swift 5
golang,Go,1.11.4,Linux,x86_64,Go,Go 1.11
scala,OpenJDK,1.8.0,Linux,x86_64,Scala,Scala 2.11.12
kotlin,OpenJDK,1.8.0,Linux,x86_64,Kotlin,Kotlin 1.3.10
rust,Rust,1.31.0,Linux,x86_64,Rust,Rust Edition 2018
php,PHP,7.2,Linux,x86_64,PHP,PHP 7
''') # Retrieved 2019-06-20 from https://support.leetcode.com/hc/en-us/articles/360011833974-What-are-the-environments-for-the-programming-languages-

    def http_request(self, request):
        request.add_header('Referer', f'https://{self.netloc}/')
        request.add_header('X-Requested-With', 'XMLHttpRequest')
        if request.get_header('Content-type') == self.JSON:
            request.add_header("X-CSRFToken", self.get_cookie("csrftoken"))
        return super().http_request(request)

    def http_response(self, request, response):
        response = super().http_response(request, response)
        if response.getcode() == 403:
            raise AuthError()
        if response.getcode() == 429:
            sleep(10)
        return response

    def pid(self, o):
        return o.path.strip("/").split("/",2)[1]

    def login(self):
        data = {"csrfmiddlewaretoken": self.get_csrftoken()}
        data.update(self.credential)

        self.raw_open(
            "/accounts/login/",
            data,
            {'Content-Type': self.URLENCODE})

    def get_csrftoken(self):
        if self.get_cookie("csrftoken") is None:
            self.raw_open("/")
        return self.get_cookie("csrftoken")

    def submit(self, pid, env, code):
        self.get_csrftoken()
        parts = pid.split('-', 1)

        if parts[0].isdigit():
            questionId = int(parts[0])
            pid = parts[1]
        else:
            response = self.open(
                "/graphql",
                { "operationName": "questionData",
                  "query": "query questionData($titleSlug: String!) { question(titleSlug: $titleSlug) { questionId } }",
                  "variables": {
                      "titleSlug": pid
                  }
                },
                {"Content-Type": self.JSON})
            questionId = response.body["data"]["question"]["questionId"]

        response = self.open(
            f"/problems/{pid}/submit/",
            { "typed_code": code.decode(),
              "question_id": questionId,
              "lang": env },
            {"Content-Type": self.JSON})
        submission_id = response.body["submission_id"]
        return f"https://{self.netloc}/submissions/detail/{submission_id}/"

    def status(self, token):
        token = urlparse(token).path.rstrip("/").rsplit("/", 1)[1]
        response = self.open(f"/submissions/detail/{token}/check/")

        data = response.body
        state = data["state"]

        if state != "SUCCESS":
            return None, state

        msg = data["status_msg"]
        code = data["status_code"]
        if code == 10:
            return (True,
                    msg,
                    {'memory': data["status_memory"],
                     'runtime': data["status_runtime"]})

        error = "full_" + "_".join(s.lower() for s in msg.split())
        if error in data:
            return False, data[error]

        return False, msg

    def snippet(self, pid, env):
        self.get_csrftoken()
        parts = pid.split('-', 1)
        if parts[0].isdigit():
            pid = parts[1]
        response = self.open(
            "/graphql",
            { "operationName": "questionData",
              "query": "query questionData($titleSlug: String!) { question(titleSlug: $titleSlug) { codeSnippets { langSlug code } } }",
              "variables": {
                  "titleSlug": pid
              }
            },
            {"Content-Type": self.JSON})

        for s in response.body["data"]["question"]["codeSnippets"]:
            if s['langSlug'] == env:
                return s['code']

    def prologue(self, pid):
        snippet = self.snippet(pid, 'c')
        snippet = snippet.rstrip()
        assert snippet.endswith("}")
        snippet = snippet[:-1].rstrip()
        assert snippet.endswith("{")
        snippet = snippet[:-1].rstrip() + ";\n"
        return snippet.encode()
