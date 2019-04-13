from itertools import zip_longest


def match_plain(s):
    def match(expected):
        if expected.startswith(s):
            return expected[len(s):]
    return match


def match_float(f, prec):
    def match(expected):
        s = expected
        if s.startswith(b'-'):
            s = s[1:]
        s = s.lstrip(b'0123456789')
        if s.startswith(b'.'):
            s = s[1:].lstrip(b'0123456789')
        if s.startswith(b'e'):
            s = s[1:]
            if s.startswith(b'-'):
                s = s[1:]
            s = s.lstrip(b'0123456789')
        l = len(expected) - len(s)

        try:
            if abs(f - float(expected[:l])) < 0.1**prec:
                return expected[l:]
        except ValueError:
            pass

    return match


def split(s):
    while s:
        segs = s.split(b'\x1bX', maxsplit=1)
        yield match_plain(segs[0])
        if len(segs) == 1:
            return

        [c, s] = segs[1].split(b'\x1b\\', maxsplit=1)
        if c.startswith(b'f.'):
            prec = int(c[2:])

            s1 = s
            if s1.startswith(b'-'):
                s1 = s1[1:]

            s1 = s1.lstrip(b'0123456789')
            if s1.startswith(b'.'):
                l = len(s)-len(s1) + 1 + prec
                try:
                    f = float(s[:l])
                    yield match_float(f, prec-1)
                    s = s[l:]
                    continue
                except ValueError:
                    pass

        yield None


def compare_line(got, expected):
    for match in split(got):
        if match is None:
            return False
        expected = match(expected)
        if expected is None:
            return False

    return expected == b''


def compare_output(got, expected):
    for (n, (g, e)) in enumerate(zip_longest(got.splitlines(), expected.splitlines())):
        if g is None:
            print("got {} lines, but more is expected".format(n))
            return False
        if e is None:
            print("{} lines is expected, but got more".format(n))
            return False

        if not compare_line(g, e):
            print("Output differs at line {}".format(n+1))
            print("Got:")
            print("   ", repr(g))
            print("Expected:")
            print("   ", repr(e))
            return False

    return True
