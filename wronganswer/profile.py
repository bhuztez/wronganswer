import os
import sys
from abc import ABC, abstractmethod
from pkg_resources import load_entry_point
from urllib.parse import urlparse
from collections import namedtuple
import csv
from io import StringIO
from subprocess import Popen, PIPE
import logging
from . import task
from .judge import compare_output
from .asm import escape_source, llvm_target

import platform
if platform.system() == 'Windows':
    from subprocess import list2cmdline as quote_argv
else:
    from pipes import quote
    def quote_argv(argv):
        return " ".join(quote(a) for a in argv)

logger = logging.getLogger(__package__)

Env = namedtuple('Env', ['code','name','ver','os','arch','lang','lang_ver'])


class AuthError(BaseException):
    pass

class Persistable(ABC):

    @abstractmethod
    def __getstate__(self):
        pass

    @abstractmethod
    def __setstate__(self, state):
        pass


@task("Fetch testcases of {pid} from {oj}")
def testcases(client, oj, pid, writer):
    return client.testcases(pid, writer)

@task("Check against testcase {name}")
async def run_test(name, argv, input, output):
    logger.debug("%.0s `%s`", "Running", quote_argv(argv))
    p = Popen(argv,stdin=PIPE,stdout=PIPE)
    got, _ = p.communicate(input.read())
    assert p.returncode == 0, "Exit code = {}".format(p.returncode)
    assert compare_output(got, output.read()), "Wrong Answer"

def index_of(l, x):
    try:
        return l.index(x)
    except ValueError:
        return len(l)

class Profile:

    def __init__(self, get_credential=None, state_store=None, cache_store=None):
        self.agents = {}

        self._get_credential = get_credential
        if get_credential is None:
            if sys.stdin.isatty():
                from .credential import readline_get_credential
                self._get_credential = readline_get_credential
            if 'TRAVIS_JOB_ID' in os.environ:
                from .credential import environ_get_credential
                self._get_credential = environ_get_credential

        self.state_store = state_store
        if state_store is None:
            from .state.user import UserStateStore
            self.state_store = UserStateStore()
        self.cache_store = cache_store
        if cache_store is None:
            from .cache.user import UserCacheStore
            self.cache_store = UserCacheStore()

        self.debug = False

    def set_debug(self, debug):
        self.debug = debug

    def __repr__(self):
        return "<{} credential={!r} state_store={!r} cache_store={!r}>".format(self.__class__.__name__, self._get_credential, self.state_store, self.cache_store)

    def get_agent(self, name='localhost'):
        if name not in self.agents:
            try:
                klass = load_entry_point(__package__, "online_judge_agents", name)
            except ImportError:
                assert False, f"agent '{name}' not found"
            agent = klass(self, name)
            self.load_state(name, agent)
            self.agents[name] = agent

        return self.agents[name]

    def get_client(self, oj):
        return self.get_agent().get_client(oj)

    def get_envs(self, oj):
        try:
            client = self.get_client(oj)
        except AssertionError:
            return []

        for v in csv.reader(StringIO(client.submit.__doc__.strip())):
            yield Env._make(v)

    def get_env(self, oj, code):
        for env in self.get_envs(oj):
            if env.code == code:
                return env

    @task("Extract problem ID from URL '{url}'")
    def pid(self, url):
        o = urlparse(url)
        client = self.get_client(o.netloc)
        return client.pid(o)

    @task("Load testcases of problem {pid} of {oj}")
    async def testcases(self, oj, pid):
        client = self.get_client(oj)
        key = getattr(client, 'CACHE_KEY', oj)
        reader = self.cache_store.get(key, pid)
        if reader is None:
            writer = self.cache_store.create(key, pid)
            await testcases(client, oj, pid, writer)
            reader = self.cache_store.get(key, pid)
        return reader

    @task("Test solution of problem {pid} of {oj}")
    async def run_tests(self, oj, pid, names, argv):
        reader = await self.testcases(oj, pid)
        for name in names or reader:
            input, output = reader[name]
            await run_test(name, argv, input, output)

    def raw_submit(self, oj, pid, env, code, agent="localhost"):
        logger.debug("%s", self.get_env(oj, env))
        return self.get_agent(agent).submit(oj, pid, env, code)

    @task("Check status of submission {token}")
    def status(self, oj, token, agent="localhost"):
        return self.get_agent(agent).status(oj, token)

    @task("Submit solution to problem {pid} in {env} to {oj} via {agent}")
    async def submit(self, oj, pid, env, code, agent="localhost"):
        token = await self.raw_submit(oj, pid, env, code, agent)
        status = None
        while status is None:
            status, message, *extra = await self.status(oj, token)
        assert status, message
        return message, extra[0]

    def _asm_pick_env(self, oj):
        envs = self.get_envs(oj)
        envs = [c for c in envs
                if c.lang == "C" and c.name in ("GCC", "MinGW")]
        envs.sort(key=lambda c:
                  (index_of(['Linux','Windows'], c.os),
                   index_of(['x86_64','x86'], c.arch)))
        assert envs
        if envs:
            return envs[0]

    def asm_llvm_target(self, oj):
        return llvm_target(self._asm_pick_env(oj))

    @task("Escape assembly code")
    async def asm2c(self, oj, pid, source):
        env = self._asm_pick_env(oj)
        client = self.get_client(oj)
        prologue = await client.prologue(pid)
        return env.code, prologue + escape_source(source)

    def load_state(self, netloc, client):
        if isinstance(client, Persistable):
            state = self.state_store.load(netloc)
            if state is not None:
                client.__setstate__(state)

    @task("Log into {netloc}", retry=True)
    async def auth(self, netloc, client):
        cred = None
        while True:
            try:
                await client.login(cred)
                if isinstance(client, Persistable):
                    self.state_store.store(netloc, client.__getstate__())
                return
            except AuthError as e:
                logger.warning("Login failed, %s", e)
                if not self._get_credential:
                    raise
                cred = self._get_credential(netloc, client.login.__annotations__['credential'])
