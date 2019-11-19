import re
import collections
from myPEG import *

class Form:
    def __init__(self, members=[]):
        self.members = members

    def __str__(self):
        return self.__repr__()

    def lit(self):
        return None

    def reduce(self):
        return self

    @staticmethod
    def Parse(ln: str):
        # parsing
        Token = collections.namedtuple('Token', ['type', 'value', 'pos'])

        def tokenize(line):
            keywords = {'T', 'F'}
            token_specification = [
                ('NEG', r'\!'),
                ('CONJ', r'\&\&'),
                ('DISJ', r'\|\|'),
                ('IMPL', r'\=\>'),
                ('BIIMPL', r'\<\>'),
                ('OPSCOBE', r'\('),
                ('CLSCOBE', r'\)'),
                ('NAME', r'[A-Za-z][A-Za-z0-9]*'),
                ('MISMATCH', r'.'),
            ]
            tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
            line_num = 1
            line_start = 0
            for mo in re.finditer(tok_regex, line):
                kind = mo.lastgroup
                value = mo.group()
                column = mo.start() - line_start

                if kind == 'MISMATCH':
                    raise RuntimeError('{value!r} unexpected on line {line_num}')

                yield Token(kind, value, column)

        tokens = list(tokenize(ln))

        postfix = []
        opstack = []
        precs = {
            'OPSCOBE': 5,
            'NEG': 4,
            'CONJ': 3,
            'DISJ': 2,
            'IMPL': 1,
            'BIIMPL': 0}
        for i, token in enumerate(tokens):
            if token[0] in ['NAME', 'T', 'F']:
                token = Token('NAME', token[1], token[2])
                postfix.append(token)
            elif token[0] in ['NEG', 'CONJ', 'DISJ', 'IMPL', 'BIIMPL']:
                while len(opstack) > 0 and opstack[-1][0] != 'OPSCOBE' and (
                        precs[opstack[-1][0]] > precs[token[0]] or
                        precs[opstack[-1][0]] == precs[token[0]] and
                        opstack[-1][0] in ['CONJ', 'DISJ', 'IMPL', 'BIIMPL']):
                    postfix.append(opstack.pop())
                opstack.append(token)
            elif token[0] == 'OPSCOBE':
                opstack.append(token)
            elif token[0] == 'CLSCOBE':
                k = 0
                while len(opstack) > 0 and opstack[-1][0] != 'OPSCOBE':
                    postfix.append(opstack.pop())
                    k = k + 1
                if opstack[-1][0] == 'OPSCOBE':
                    opstack.pop()
                else:
                    raise RuntimeError('Scobe error')

        while len(opstack) > 0:
            postfix.append(opstack.pop())

        stack = []
        while len(postfix) > 0:
            token = postfix.pop(0)
            if token[1] in ['T', 'True']:
                stack.append(ConForm())
            elif token[1] in ['F', 'False']:
                stack.append(DisForm())
            elif token[0] == 'NAME':
                stack.append(AtomForm(token[1]))
            elif token[0] == 'NEG':
                stack.append(NegForm(stack.pop()))
            elif token[0] == 'CONJ':
                l = [stack.pop(), stack.pop()]
                l.reverse()
                stack.append(ConForm(l))
            elif token[0] == 'DISJ':
                l = [stack.pop(), stack.pop()]
                l.reverse()
                stack.append(DisForm(l))
            elif token[0] == 'IMPL':
                l = [stack.pop(), stack.pop()]
                l.reverse()
                stack.append(DisForm([NegForm(l[0]), l[1]]))
            elif token[0] == 'BIIMPL':
                l = [stack.pop(), stack.pop()]
                l.reverse()
                stack.append(DisForm([ConForm([l[0], l[1]]), ConForm([NegForm(l[0]), NegForm(l[1])])]))
        return stack.pop()

    def __hash__(self):
        return self.__repr__().__hash__()

    def __eq__(self, other):
        return hash(self) == hash(other) or str(self) == str(other) or str(self.reduce()) == str(other.reduce())


class AtomForm(Form):
    def __init__(self, name):
        self.name = name
        self.members = None

    framed = False

    def copy(self):
        return AtomForm(self.name)

    def __repr__(self, br=False):
        if self.framed:
            m = '[{}]'
        else:
            m = '{}'
        return m.format(str(self.name))


class NegForm(Form):
    def __init__(self, value):
        self.value = value

    def reduce(self):
        t = type(self.value)
        if t is AtomForm:
            return self
        elif t is NegForm:
            return self.value.value.reduce()
        else:
            m = [NegForm(memb).reduce() for memb in self.value.members]
            if t is ConForm:
                r = DisForm(m)
            else:
                r = ConForm(m)
            # print(self,'2',r.reduce())
            return r.reduce()

    def lit(self):
        return self.value.lit()

    def __repr__(self, br=False):
        return ('!{}' if type(self.value) in [AtomForm, NegForm] else '!({})').format(str(self.value))


class SetForm(Form):
    def lit(self):
        return set.union(*[a.lit() for a in self.members])


class ConForm(SetForm):
    def __init__(self, members=[]):
        m = []
        for mm in members:
            if type(mm) is ConForm and len(mm.members) > 0:
                m.extend(mm.members)
            else:
                m.append(mm)
        self.members = m.copy()

    def reduce(self):
        r = [memb.reduce() for memb in self.members]
        r1 = []
        for t in r:
            if str(t) == 'False':
                return DisForm([])
            if str(t) != 'True':
                r1.append(t)
        return ConForm(r1)

    def __repr__(self, br=False):
        return 'True' if len(self.members) == 0 else ('({})' if br else '{}').format(
            '&&'.join([a.__repr__(br=(type(a) == DisForm)) for a in self.members]))


class DisForm(SetForm):
    def __init__(self, members=[]):
        m = []
        for mm in members:
            if type(mm) is DisForm and len(mm.members) > 0:
                m.extend(mm.members)
            else:
                m.append(mm)
        self.members = m.copy()

    def reduce(self):
        # return DisForm([memb.reduce() for memb in self.members])

        r = [memb.reduce() for memb in self.members]
        r1 = []
        for t in r:
            if str(t) == 'True':
                return ConForm([])
            if str(t) != 'False':
                r1.append(t)
        return DisForm(r1)

    def __repr__(self, br=False):
        return 'False' if len(self.members) == 0 else ('({})' if br else '{}').format(
            '||'.join([str(a) for a in self.members]))


parser=PEG(
    ''



)



# res = [Form.Parse("A||B"), Form.Parse("A&&B"), Form.Parse("A>>B"), Form.Parse("!A<>B"), Form.Parse("C&&(A||B)"),
#        Form.Parse("!C&&!(A<>!B||T)")]
#
# print(res)
# print([r.reduce() for r in res])
# print([r.reduce().reduce() for r in res])


# formula ::= atom |
#   (formula) |
#   formula || formula |
#   formula && formula |
#   formula >> formula |
#   -- formula |
#   QA var formula |
#   QE var formula
# atom ::= name( arglist )
# arglist ::= arg | arg, arglist
# arg ::= const | function | var
# const ::= "name"
# function ::= name( arglist )
# var :: name
