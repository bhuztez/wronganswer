from itertools import product
import re


GLOBL = re.compile(rb'^\s+[.]globl\s+(\S+)$', re.M)
LABEL = re.compile(rb'^([^:\s]+):$', re.M)
COMMENT= re.compile(rb'\s+\#.*$', re.M)

def encode_int(n):
    while True:
        yield b'_.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'[n % 64]
        if n == 0:
            break
        n //= 64

def relabel(code):
    code = COMMENT.sub(b'', code)
    labels = set(LABEL.findall(code)) - set(GLOBL.findall(code))
    pattern = b"|".join(map(re.escape, labels))
    labels = {l: b"L"+bytes(encode_int(n))
              for n,l in enumerate(labels)}
    def repl(m):
        return labels[m.group(0)]
    return re.sub(pattern, repl, code)


class Node(object):
    __slots__ = ('value','prev','next')


    def __init__(self,value,prev=None,next=None):
        self.value = value
        self.prev = self if prev is None else prev
        self.next = self if next is None else next
        if prev is not None:
            prev.next = self
        if next is not None:
            next.prev = self


    def __iter__(self):
        n = self.next
        while n is not self:
            yield n
            n = n.next


    def __repr__(self):
        if self.value < 0:
            return " ".join(repr(n) for n in self)
        elif self.value < 256:
            return repr(chr(self.value))
        else:
            return repr(self.value)


class Grammar(object):
    __slots__ = ('rules','counts','digram','next_rule','endpoint')


    def __init__(self, source):
        self.rules = {}
        self.counts = {}
        self.digram = {i:{} for i in range(256)}
        self.next_rule = 256
        self.endpoint = Node(-1)

        for i,c in enumerate(source):
            self.append(c)


    def delete_digram(self, node):
        if node.value == node.next.value:
            if node.prev.value == node.value:
                return
            if node.next.next.value == node.value:
                self.digram[node.value][node.value]=node.next
                return
        del self.digram[node.value][node.next.value]


    def push(self,value,endpoint):
        node = Node(value,endpoint.prev,endpoint)

        if value >= 256:
            # if endpoint is not self.endpoint:
            #     if endpoint.prev.value != value:
            #         assert self.counts[value] > 0
            self.counts[value] += 1


    def remove(self,node):
        if node.prev.value >= 0:
            self.delete_digram(node.prev)
        if node.next.value >= 0:
            self.delete_digram(node)

        node.next.prev = node.prev
        node.prev.next = node.next

        node.prev = None
        node.next = None

        if node.value >= 256:
            self.counts[node.value] -= 1


    def new_rule(self, node):
        n = self.next_rule
        self.next_rule += 1
        self.digram[n] = {}
        self.digram[node.value][node.next.value]=n

        if node.prev.value >= 0:
            self.delete_digram(node.prev)
        if node.next.next.value >= 0:
            self.delete_digram(node.next)

        self.counts[n] = 1

        new_node = Node(n,node.prev,node.next.next)
        rule=Node(-n,node.next,node)
        self.rules[n] = rule

        if new_node.prev.value >= 0:
            self.digram[new_node.prev.value][n] = new_node.prev

        if new_node.next.value >= 0:
            self.digram[n][new_node.next.value] = new_node

        return n


    def append(self, value):
        stack = [(value,self.endpoint)]

        while stack:
            value, endpoint = stack.pop()
            last = endpoint.prev
            if last is endpoint:
                self.push(value,endpoint)
                continue

            match = self.digram[last.value].get(value,None)
            if match is None:
                self.push(value,endpoint)
                self.digram[last.value][value]=last
                continue

            if isinstance(match,Node):
                if match.next is last:
                    # triples
                    self.push(value,endpoint)
                    continue

                if match.prev.value < 0 and match.prev is match.next.next:
                    self.digram[last.value][value]=-match.prev.value
                    match=-match.prev.value


            self.remove(last)

            if isinstance(match,int):
                stack.append((match,endpoint))
                continue

            if (match.value < 256) or (self.counts[match.value] > 1):
                rule = self.new_rule(match)
                stack.append((rule,endpoint))
                continue

            # this is the only occurrence of match.value
            self.remove(match.next)

            if match.next.value >= 0:
                self.digram[match.value][match.next.value] = match

            rule = self.rules[match.value]

            stack.append((match.value,endpoint))
            stack.append((value,rule))

            if rule.next.next is rule.prev:
                self.digram[rule.next.value][rule.prev.value]=rule.next


def tsort(rules):
    visited = set()

    for rule in rules:
        if rule < 256 or rule in visited:
            continue

        stack = [rule]
        backtrack = [rules[rule].next]

        while True:
            rule = stack[-1]
            node = backtrack.pop()
            if node is rules[rule]:
                stack.pop()
                visited.add(rule)
                yield rule
                if not stack:
                    break
            else:
                assert node.value not in stack
                backtrack.append(node.next)
                if node.value < 256 or node.value in visited:
                    continue
                stack.append(node.value)
                backtrack.append(rules[node.value].next)


def copy_rule(endpoint):
    new_node = Node(-1)
    for n in endpoint:
        Node(n.value,new_node.prev,new_node)
    return new_node


def replace(node,endpoint):
    new_node = copy_rule(endpoint)
    node.prev.next, node.next.prev = new_node.next, new_node.prev
    new_node.next.prev, new_node.prev.next = node.prev, node.next
    new_node.prev, new_node.next, node.prev, node.next = None, None, None, None


ESCAPE_CHARS = b'\\\n\t\"'


def normalize_rules(endpoint,rules,counts):
    length = {}
    same_as = {}

    def length_of(key):
        if key < 256:
            return 2 if key in ESCAPE_CHARS else 1
        else:
            return length[key]

    def rewrite(endpoint):
        node = endpoint.next
        while node is not endpoint:
            value = node.value
            if value in same_as:
                node.value = same_as[value]
                value = node.value
            node = node.next
            if value < 256:
                continue
            if length[value] > 3 and counts[value] > 1:
                continue

            replace(node.prev,rules[value])

    keys = list(tsort(rules))

    for key in keys:
        length[key] = sum(length_of(n.value) for n in rules[key])
        node = rules[key].next
        if node.prev is node.next:
            same_as[key]=same_as.get(node.value,node.value)
        else:
            rewrite(node.prev)

    rewrite(endpoint)

    # assert len(same_as) == 0

    for key in same_as:
        del rules[key]
        del length[key]
        del counts[key]

    keys = [key for key in keys if key not in same_as]
    keys.reverse()


    for key in keys:
        if length[key] < 4 or counts[key] < 2:
            del rules[key]
            del length[key]
            del counts[key]
            continue

        for node in rules[key]:
            if node.value < 256:
                continue
            counts[node.value] += counts[key]-1


def rule_length(endpoint,length):
    node = endpoint.next

    acc = 0
    is_char = True

    while node is not endpoint:
        if node.value < 256:
            acc += 2 if node.value in ESCAPE_CHARS else 1
            is_char = True
        else:
            l = length[node.value]
            if l >= 0:
                is_char = True
                acc += l
            else:
                acc += -l + 1
                if is_char:
                    acc += 1
                is_char = False

        node = node.next

    if not is_char:
        acc += 1

    return acc


CHARS=b"_abcdefghijlkmnopqrstvwxyzABCDEFGHIJKMNOPQSTVWXYZ"


def assign_token(endpoint,rules,counts):
    keys = list(rules.keys())
    keys.sort(key=lambda x:counts[x])

    repeat = 0
    length = {}
    d = {}

    while keys:
        repeat += 1

        for c in product(CHARS,repeat=repeat):
            token = bytes(c)

            while keys:
                rule = keys.pop()
                l = rule_length(rules[rule], length)
                cost = 12 + (l-repeat-3) - counts[rule] * (l-repeat-3)
                if cost >= 0:
                    length[rule]=l
                    continue

                length[rule]=-repeat
                d[rule]=token
                break

            if not keys:
                break

    keys = list(rules.keys())
    keys.sort(key=lambda x:counts[x],reverse=True)

    def rewrite(endpoint):
        node = endpoint.next
        while node is not endpoint:
            value = node.value
            node = node.next
            if (value < 256) or (value in d):
                continue
            replace(node.prev,rules[value])

    for key in keys:
        rewrite(rules[key])

    rewrite(endpoint)

    def _expand_rule(endpoint):
        is_char = True
        node = endpoint.next

        while node is not endpoint:
            if node.value < 256:
                if not is_char:
                    yield b'"'
                if node.value in ESCAPE_CHARS:
                    yield {b'\\':b'\\\\',b'\"':rb'\"',b'\n':rb'\n',b'\t':rb'\t'}[bytes((node.value,))]
                else:
                    yield bytes((node.value,))
                is_char = True
            else:
                yield b'"' if is_char else b' '
                yield d[node.value]
                is_char = False

            node = node.next

        if not is_char:
            yield b'"'

    def expand_rule(endpoint):
        return b"".join(_expand_rule(endpoint))

    def rule_def(rule):
        return b'#define ' + d[rule] + b' "' + expand_rule(rules[rule]) + b'"\n'

    return b"".join(rule_def(key) for key in keys if key in d) + b'__asm__("' + expand_rule(endpoint) + b'");'


def rule_text(endpoint,rules):
    for node in endpoint:
        if node.value < 256:
            yield bytes((node.value,))
        else:
            for c in rule_text(rules[node.value],rules):
                yield c


def compress(source):
    g = Grammar(source)
    endpoint = g.endpoint
    rules = g.rules
    counts = g.counts

    # assert b"".join(rule_text(endpoint,rules))==source
    normalize_rules(endpoint,rules,counts)
    # assert b"".join(rule_text(endpoint,rules))==source

    compressed = assign_token(endpoint,rules,counts)
    assert b"".join(rule_text(endpoint,rules))==source

    return compressed


def escape_source(source):
    return compress(relabel(source))

def llvm_target(env):
    return "{}-{}-gnu".format(
        {"x86": "i686", "x86_64": "x86_64"}[env.arch],
        {"Windows": "pc-windows", "Linux": "unknown-linux"}[env.os])
