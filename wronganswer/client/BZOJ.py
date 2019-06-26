from urllib.parse import parse_qs, urlencode, urlparse
from ..http import HTTP
from ..profile import AuthError
from . import Judge


class BZOJClient(HTTP, Judge):
    CREDENTIAL: [
        ("user_id", "User ID", False),
        ("password", "Password", True)
    ]

    ENV: (
'''
0,GCC,4.4.5,Linux,x86,C,C99
1,GCC,4.4.5,Linux,x86,C++,C++03
2,FreePascal,2.4.0,Linux,x86,Pascal,Free Pascal
3,OpenJDK,1.6.0_22,Linux,x86,Java,Java 6
''') # Retrieved 2019-06-25 from https://www.lydsy.com/JudgeOnline/

    def http_response(self, request, response):
        response = super().http_response(request, response)
        if request.get_method() == "POST":
            if request.full_url.endswith('submit.php') and not (response.getcode() == 302 and response.info()['location'].startswith('./status.php?')):
                raise AuthError("login required")
        return response

    def pid(self, o):
        return parse_qs(o.query)["id"][0]

    def login(self):
        response = self.raw_open("/JudgeOnline/login.php", self.credential, {'Content-Type': self.URLENCODE})
        text = response.body.find(".//script").text.strip()
        if text != "history.go(-2);":
            raise AuthError("UserName or Password Wrong!")

    def submit(self, pid, env, code):
        last_sid = self.get_last_sid(pid, env)
        response = self.open(
            "/JudgeOnline/submit.php",
            { "source": code,
              "id": pid,
              "language": env,
              "submit": "Submit"},
            {'Content-Type': self.URLENCODE})
        sid = self.get_first_sid_since(pid, env, last_sid, code)
        return "https://www.lydsy.com/JudgeOnline/showsource.php?" + urlencode({"id": sid})

    def get_last_sid(self, pid, env):
        status_list = self.status_list()
        if status_list:
            return status_list[0]["sid"]

    def get_first_sid_since(self, pid, env, last_sid, code):
        status_list = self.status_list(self.credential["user_id"], pid, env)
        status_list.reverse()
        for s in status_list:
            if int(s["sid"]) <= int(last_sid):
                continue
            submission = self.submission(s["sid"])
            if code == submission:
                return s["sid"]

    def submission(self, sid):
        response = self.open(
            "/JudgeOnline/showsource.php",
            {"id": sid})
        html = response.body
        code = html.findtext(".//pre")
        _, code = code.split("\n\n", 1)
        return code[:-1].encode()

    def status_list(self, uid=None, pid=None, env=None, top=None, result=None):
        response = self.open(
            "/JudgeOnline/status.php",
            { "problem_id": pid or "",
              "user_id": uid or "",
              "jresult": result or "-1",
              "language": env or "-1",
              "top": top or "-1"},
            method="GET")

        html = response.body
        return [
            { "sid": tr.findtext("./td[1]"),
              "uid": tr.findtext("./td[2]/a"),
              "pid": tr.findtext("./td[3]/a"),
              "status": tr.findtext("./td[4]//font"),
              "color": tr.find("./td[4]//font").get("color"),
              "memory": tr.findtext("./td[5]"),
              "runtime": tr.findtext("./td[6]"),
              "size": tr.findtext("./td[8]")
            }
            for tr in html.findall(".//table[@align='center']/tbody/tr[@align='center']")]

    def status(self, token):
        token = parse_qs(urlparse(token).query)["id"][0]
        status_list = self.status_list(top=token)
        status = status_list[0]

        if status["color"] == 'green':
            return (True,
                    status["status"],
                    {'memory': status['memory'],
                     'runtime': status['runtime'],
                     'codesize': status['size']})
        elif status["color"] == 'gray':
            return None, status["status"]
        else:
            return False, status["status"]
