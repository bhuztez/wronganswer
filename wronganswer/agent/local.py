from pkg_resources import load_entry_point
from . import Agent
from ..client import Client, Judge

class LocalAgent(Agent):

    def __init__(self, profile, netloc):
        self.profile = profile
        self.clients = {}

    def get_client(self, oj, type=None):
        client = self.clients.get(oj, None)
        if client is None:
            try:
                klass = load_entry_point(__package__.split(".",1)[0], "online_judge_clients", oj)
            except ImportError:
                assert False, f'client of {oj} not found'
            client = klass(self.profile, oj)
            self.profile.load_state(client)
            self.clients[oj] = client
        assert isinstance(client, type or Client), f'{type} not supported'
        return client

    def submit(self, oj, pid, env, code):
        client = self.get_client(oj, Judge)
        return client.submit(pid, env, code)

    def status(self, oj, token):
        client = self.get_client(oj, Judge)
        return client.status(token)
