from base64 import b64encode
from urllib.parse import parse_qs, urlencode, urlparse
from .. import task
from ..profile import AuthError
from ..http import HTTP
from . import Judge


class POJClient(HTTP, Judge):
    scheme = 'http'
    CREDENTIAL: [
        ("user_id1", "User ID", False),
        ("password1", "Password", True)
    ]

    ENV: (
'''
0,MinGW,4.4.0,Windows,x86,C++,C++03
1,MinGW,4.4.0,Windows,x86,C,C99
2,JDK,6,Windows,x86,Java,Java 6
3,FreePascal,2.2.0,Windows,x86,Pascal,Free Pascal
4,MSCV,2008,Windows,x86,C++,C++03
5,MSCV,2008,Windows,x86,C,C99
6,MinGW,4.4.0,Windows,x86,Fortran,Fortran 95
''')

    def http_response(self, request, response):
        response = super().http_response(request, response)
        if request.get_method() == "POST":
            if not (response.getcode() == 302 and response.info()['location'] == 'http://poj.org/status'):
                if b'Please login first.' in response.body:
                    raise AuthError("Please login first.")
                raise AuthError("Authentication Failed")
        return response

    def pid(self, o):
        return parse_qs(o.query)["id"][0]

    def login(self):
        data = {"B1": "login", "url": "/status"}
        data.update(self.credential)
        self.raw_open("/login", data, {'Content-Type': self.URLENCODE})
        response = self.raw_open("/submit")
        form = response.body.find(".[@action='login']")
        if form is not None and form.tag == 'form':
            raise AuthError("Login Required")

    def submit(self, pid, env, code):
        env = env.lstrip()
        last_sid = self.get_last_sid(pid, env)
        self.open(
            "/submit",
            { "source": b64encode(code),
              "problem_id": pid,
              "language": env,
              "submit": "Submit",
              "encoded": "1"},
            {'Content-Type': self.URLENCODE})
        sid = self.get_first_sid_since(pid, env, last_sid, code)
        return "http://poj.org/showsource?" + urlencode({"solution_id": sid})

    def get_last_sid(self, pid, env):
        status_list = self.status_list()
        if status_list:
            return status_list[0]["sid"]

    def get_first_sid_since(self, pid, env, last_sid, code):
        status_list = self.status_list(self.credential["user_id1"], pid, env, last_sid)
        status_list.reverse()
        for s in status_list:
            submission = self.submission(s["sid"])
            if code == submission:
                return s["sid"]

    def submission(self, sid):
        response = self.open(
            "/showsource",
            {"solution_id": sid})
        html = response.body
        return html.findtext(".//pre").encode()

    def status_list(self, uid=None, pid=None, env=None, bottom=None, top=None, result=None):
        response = self.open(
            "/status",
            { "problem_id": pid or "",
              "user_id": uid or "",
              "result": result or "",
              "language": env or "",
              "bottom": bottom or "",
              "top": top or ""})

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
            for tr in html.findall(".//table[@class='a']/tr[@align='center']")]

    def status(self, token):
        token = parse_qs(urlparse(token).query)["solution_id"][0]
        sid = int(token)
        status_list = self.status_list(top=sid+1)
        status = status_list[0]
        if status["color"] == 'blue':
            return (True,
                    status["status"],
                    {'memory': status['memory'],
                     'runtime': status['runtime'],
                     'codesize': status['size']})
        elif status["color"] == 'green' and status["status"] != 'Compile Error':
            return None, status["status"]
        else:
            return False, status["status"]
