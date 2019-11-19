import re
import collections


# region peg ops


class oom:
    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return '{}+'.format(self.x)


class zom:
    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return '{}*'.format(self.x)


class opt:
    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return '{}?'.format(self.x)


class chk:
    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return '&{}'.format(self.x)


class non:
    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return '!{}'.format(self.x)


class sel:
    def __init__(self, *alternatives):
        self.alternatives = list(alternatives)

    def __repr__(self):
        return ' / '.join([str(x) for x in self.alternatives])


# endregion

class TNode:
    def __init__(self, symbol):
        self.symbol = symbol
        self.childs = []

    def add(self, child):
        if not child is None:
            self.childs.append(child)

    def __repr__(self):
        if self.symbol is None or type(self.symbol) is list:
            return '{}'.format(self.childs)
        elif len(self.childs) == 0:
            return '{}'.format(self.TokRepr(self.symbol))
        elif len(self.childs) == 1:
            return '{}/{}'.format(self.TokRepr(self.symbol), self.childs[0])
        else:
            return '{}:{}'.format(self.TokRepr(self.symbol), self.childs)

    def TokRepr(self, val):
        if type(val) is Token:
            return '{} {}'.format(val.type, val.value)
        else:
            return str(val)

    def TreeRepr(self, ts=0):
        print('\t' * ts + self.TokRepr(self.symbol))
        for c in self.childs:
            c.TreeRepr(ts + 1)


Token = collections.namedtuple('Token', ['type', 'value', 'pos'])


def packrat_memoization(func):
    def mem_wrapper(self, rule, toks, i):

        key = (i, str(rule).__hash__())
        if key in self.mem:
            return self.mem[key]
        else:
            res = func(self, rule, toks, i)
            self.mem[key] = res
            return res

        # key = (i, str(rule).__hash__())
        # if key in self.mem:
        #     if self.mem[key] == 'evaluating':
        #         return None
        #     return self.mem[key]
        # else:
        #     self.mem[key] = 'evaluating'
        #     res = func(self, rule, toks, i)
        #     self.mem[key] = res
        #     return res

    return mem_wrapper


class PEG:
    def __init__(self, start: str, terms: dict, rules: dict):
        self.token_rules = terms.copy()
        self.terms = set(self.token_rules.keys())
        self.rules = rules.copy()
        self.nonterms = set(self.rules.keys())
        self.start = start
        self.mem = {}

    def _tokenize(self, line):
        '''
        Токенизация
        :param line: строка
        :return:
        '''
        # tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in self.terms_spec)
        tok_regex = '|'.join('(?P<{}>{})'.format(k, self.token_rules[k]) for k in self.token_rules)
        tok_regex += '|(?P<MISMATCH>.)'
        line_start = 0
        for mo in re.finditer(tok_regex, line):
            kind = mo.lastgroup
            value = mo.group()
            column = mo.start() - line_start

            if kind == 'MISMATCH':
                raise RuntimeError('value {} unexpected at {}'.format(value, line_start))

            yield Token(kind, value, column)

    @packrat_memoization
    def _parse(self, symbol, tokens, i):
        '''
        функция PEG разбора заданной грамматики
        :param symbol: Текущий разбираемый терминал, нетерминал или правило
        :param tokens: строка токенов
        :param i: текущая позичия указателя
        :return: дерево синтаксического разбора
        '''
        if i > len(tokens):
            return None
        if type(symbol) == str and symbol in self.terms:
            if i < len(tokens) and tokens[i].type == symbol:
                res = TNode(tokens[i])
                return res, i + 1
            else:
                return None
        elif type(symbol) == str and symbol in self.nonterms:
            rule = self.rules[symbol]
        elif type(symbol) in [str, list, chk, non, opt, zom, oom, sel]:
            rule = symbol
        else:
            raise ValueError()
        t = type(rule)
        if t is str:
            res = TNode(symbol)
            se = self._parse(rule, tokens, i)
            if se is None:
                return None
            res.add(se[0])
            return res, se[1]
        elif t is list:
            j = i
            res = TNode(symbol if type(symbol) is str else 'seq')
            for sr in rule:
                tres = self._parse(sr, tokens, j)
                if tres is None:
                    return None
                else:
                    subtree, j = tres
                    res.add(subtree)
            return res, j
        elif t is sel:
            alternatives = rule.alternatives
            for a in alternatives:
                altres = self._parse(a, tokens, i)
                if not altres is None:
                    return altres
            return None
        elif t is non:
            tmp = self._parse(rule.x, tokens, i)
            if tmp is None:
                return TNode(None), i
            else:
                return None
        elif t is chk:
            tmp = self._parse(rule.x, tokens, i)
            if tmp is None:
                return None
            else:
                return TNode(None), i
        elif t is zom:
            res = TNode('zom')
            j = i
            while True:
                tr = self._parse(rule.x, tokens, j)
                if tr is None:
                    break
                res.add(tr[0])
                j = tr[1]
            if len(res.childs) == 0:
                res = None
            return res, j
        elif t is opt:
            optional = self._parse(rule.x, tokens, i)
            if optional is None:
                return None, i
            else:
                return optional
        elif t is oom:
            one = self._parse(rule.x, tokens, i)
            if one is None:
                return None
            res = TNode('oom')
            res.add(one[0])
            j = one[1]
            while True:
                tr = self._parse(rule.x, tokens, j)
                if tr is None:
                    break
                res.add(tr[0])
                j = tr[1]
            if len(res.childs) == 0:
                res = None
            return res, j
        else:
            raise ValueError()

    def Parse(self, line):
        '''
        Разбор строки
        :param line:
        :return:
        '''
        tokens = list(self._tokenize(line))
        tokens = [t for t in tokens if t.type != 'ignore']
        res = self._parse(self.start, tokens, 0)
        self.mem = {}
        if res is None:
            return None
        elif len(tokens) > res[1]:
            raise ValueError('остались лишние токены: {}'.format(tokens[res[1]:]))
        else:
            return res[0]


if __name__ == '__main__':
    p = PEG('S',
            {
                'a': 'a'
            },
            {
                'S': 'A',
                'A': sel(['A', 'a'], 'a')
            })

    print(p.Parse('aa'))
#     # Грамматика целочисленной арифметики
#     arith = PEG('expr',
#                 {
#                     'num': r'[0-9]+(\.[0-9]*)?',
#                     'opbracket': r'\(',
#                     'clbracket': r'\)',
#                     'plus': r'\+',
#                     'minus': r'\-',
#                     'prod': r'\*',
#                     'div': r'\/',
#                     'ignore': r' +'
#                 },
#                 {
#                     'expr': 'sum',
#                     'sum': ['product', zom([sel('plus', 'minus'), 'product'])],
#                     'product': ['value', zom([sel('prod', 'div'), 'value'])],
#                     'value': [opt('minus'), sel('num', ['opbracket', 'sum', 'clbracket'])]
#                 })
#
#
#     def parsingTree2ASTree(node: TNode):
#         if len(node.childs) == 1:
#             return parsingTree2ASTree(node.childs[0])
#
#         elif node.symbol == 'value' and len(node.childs) == 2:
#             tr = TNode(node.childs[0].symbol)
#             tr.add(parsingTree2ASTree(node.childs[1]))
#             return tr
#
#         elif node.symbol in ['product', 'sum']:
#             r = TNode(node.symbol)
#             r.add(parsingTree2ASTree(node.childs[0]))
#             zcs = node.childs[1].childs
#             for seq in zcs:
#                 for c in seq.childs:
#                     if type(c) is Token:
#                         r.add(c)
#                     else:
#                         r.add(parsingTree2ASTree(c))
#             return r
#         elif node.symbol == 'seq' and node.childs[0].symbol.type == 'opbracket':
#             return parsingTree2ASTree(node.childs[1])
#
#         elif True:
#             return node
#
#
#     def eval_arythm(node):
#         if type(node.symbol) is Token and node.symbol.type == 'num':
#             return float(node.symbol.value)
#         elif node.symbol == 'sum':
#             r = eval_arythm(node.childs[0])
#             for i in range(2, len(node.childs), 2):
#                 if node.childs[i - 1].symbol.type == 'minus':
#                     r -= eval_arythm(node.childs[i])
#                 else:
#                     r += eval_arythm(node.childs[i])
#             return r
#         elif node.symbol == 'product':
#             r = eval_arythm(node.childs[0])
#             for i in range(2, len(node.childs), 2):
#                 if node.childs[i - 1].symbol.type == 'div':
#                     r /= eval_arythm(node.childs[i])
#                 else:
#                     r *= eval_arythm(node.childs[i])
#             return r
#         elif node.symbol.type == 'minus':
#             return -eval_arythm(node.childs[0])
#         else:
#             print('{}'.format(node))
#
#
#     def testline(l, peg: PEG):
#         print('---------------')
#         print(l)
#         res = peg.Parse(l)
#         print('parsing tree:')
#         # res.TreeRepr()
#         ast = parsingTree2ASTree(res)
#         print('abstract syntax tree:')
#         ast.TreeRepr()
#         val = eval_arythm(ast)
#         print('result:')
#         print(val)
#         # print()
#
#
#     ls = [
#         '1', '0.', '0.0010', '-1', '1+2', '1*2', '1*-2', '-1*2', '1-2*3',
#         '1*2-3', '1-2/3*5+4', '1-2/(3+4)/5',
#         '345 - -56 + (1+2)', '1*2*3/(4+5)*6+-7-2',
#         '(876-787+(765-234)*2736/23/123)/23*76*5-1',
#     ]
#
#     for l in ls:
#         testline(l, arith)

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
#
# predp = PEG('expr',
#             {
#                 'NEG': r'\-',
#                 'CONJ': r'\&',
#                 'DISJ': r'\|',
#                 'IMPL': r'\>',
#                 'ALLQ': r'\@',
#                 'EXQ': r'\#',
#                 'OPRNTH': r'\(',
#                 'CPRNTH': r'\)',
#                 'TRUTH': r'[1T]',
#                 'FALSE': r'[0F]',
#                 'NAME': r'[A-Za-z][A-Za-z0-9]*',
#                 'COMMA': r','
#             },
#             {
#                 'expr': sel('atomic', ['expr', 'IMPL', 'expr'], ['expr', 'DISJ', 'expr'], ['expr', 'CONJ', 'expr']),
#                 'atomic': sel('atom', ['NEG', 'atomic'], ['OPRNTH', 'expr', 'CPRNTH']),
#                 'atom': sel('TRUTH', 'FALSE', 'qexpression', 'predicate'),
#                 'qexpression': ['quantifier', 'name', 'predicate'],
#             })
#
# # ls = ['(876-787+(765-234)*2736/23)/23*765-1', '345 - -56']
# #
# # for l in ls:
# #     testline(l, predp)
