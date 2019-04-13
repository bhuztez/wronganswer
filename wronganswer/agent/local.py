from pkg_resources import load_entry_point
from . import Agent


class LocalAgent(Agent):

    def __init__(self, profile, netloc):
        self.profile = profile
        self.clients = {}

    def get_client(self, oj):
        if oj not in self.clients:
            try:
                klass = load_entry_point(__package__.split(".",1)[0], "online_judge_clients", oj)
            except ImportError:
                assert False, f'client of {oj} not found'
            client = klass(self.profile, oj)
            self.profile.load_state(oj, client)
            self.clients[oj] = client
        return self.clients[oj]

    def submit(self, oj, pid, env, code):
        client = self.get_client(oj)
        return client.submit(pid, env, code)

    def status(self, oj, token):
        client = self.get_client(oj)
        return client.status(token)
