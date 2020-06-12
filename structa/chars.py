class Digit:
    pass

class OctDigit(Digit):
    display = 'O'
    chars = set('01234567')

class DecDigit(Digit):
    display = 'D'
    chars = set('0123456789')

class HexDigit(Digit):
    display = 'X'
    chars = set('0123456789abcdefABCDEF')

class AnyChar:
    display = '.'
