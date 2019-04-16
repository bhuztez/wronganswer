import readline
from getpass import getpass


def readline_get_credential(oj, fields):
    credential = {}
    for key, desc, is_password in fields:
        default = credential.get(key, '')
        desc = desc + " for " + oj
        if is_password:
            if default:
                result = getpass(desc + " (use old if left blank): ") or default
            else:
                result = getpass(desc + ": ")
        else:
            readline.set_startup_hook(lambda: readline.insert_text(default))
            try:
                result = input(desc + ": ")
            finally:
                readline.set_startup_hook()
        credential[key] = result
    return credential


def environ_get_credential(oj, fields):
    import os
    credential = {}
    for key, desc, is_password in fields:
        credential[key] = os.environ["".join(c.lower().capitalize().replace("-",'_') for c in oj.split(".")) + '_' + key]
    return credential
