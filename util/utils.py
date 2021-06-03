from random import randint


def randstr(length):
    ret = ""
    pool = "qwertyuioplkjhgfdsazxcvbnmQWERTYUIOPLKJHGFDSAZXCVBNM1234567890"
    for _ in range(length):
        ret += pool[randint(0, len(pool)-1)]
    return ret
