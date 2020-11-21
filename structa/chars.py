class Digit:
    pass


class OctDigit(Digit):
    display = 'O'
    chars = set('01234567')

    def __repr__(self):
        return 'OctDigit'


class DecDigit(Digit):
    display = 'D'
    chars = set('0123456789')

    def __repr__(self):
        return 'DecDigit'


class HexDigit(Digit):
    display = 'X'
    chars = set('0123456789abcdefABCDEF')

    def __repr__(self):
        return 'DecDigit'


class AnyChar:
    display = '.'

    def __repr__(self):
        return 'AnyChar'


OctDigit = OctDigit()
DecDigit = DecDigit()
HexDigit = HexDigit()
AnyChar = AnyChar()
