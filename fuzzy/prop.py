from myPEG import *


class Form:

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return self.__repr__().__hash__()


class AtomForm(Form):
    def __init__(self, name):
        super(Form, self).__init__()
        self.name = name

    #
    # def copy(self):
    #     return AtomForm(self.name)

    def __repr__(self, br=False):
        return self.name


class NegForm(Form):
    def __init__(self, value):
        super(Form, self).__init__()
        self.value = value

    def __repr__(self, br=False):
        return ('~{}' if type(self.value) in [AtomForm, NegForm] else '~({})').format(self.value)


class SetForm(Form):
    def __init__(self, members=None):
        super().__init__()
        if members is None:
            self.members = []
        else:
            self.members = members.copy()


class ConForm(SetForm):
    def __init__(self, members):
        super().__init__(members)
        # self.members.extend(members)
        # self.members.extend(members)

    def __repr__(self, br=False):
        return '1' if len(self.members) == 0 else ('({})' if br else '{}').format(
            '&'.join([a.__repr__(br=(type(a) == DisForm)) for a in self.members]))


class DisForm(SetForm):
    def __init__(self, members):
        super().__init__(members)
        # self.members.extend(members)

    #
    # def reduce(self):
    #     # return DisForm([memb.reduce() for memb in self.members])
    #
    #     r = [memb.reduce() for memb in self.members]
    #     r1 = []
    #     for t in r:
    #         if str(t) == 'True':
    #             return ConForm([])
    #         if str(t) != 'False':
    #             r1.append(t)
    #     return DisForm(r1)

    def __repr__(self, br=False):
        return '0' if len(self.members) == 0 else ('({})' if br else '{}').format(
            '|'.join([str(a) for a in self.members]))


class ImpForm(Form):
    def __init__(self, a: Form, b: Form):
        super().__init__()
        self.a = a
        self.b = b

    def __repr__(self):
        sa = ('({})' if type(self.a) in [ImpForm, EstForm] else '{}').format(self.a)
        sb = ('({})' if type(self.b) in [ImpForm, EstForm] else '{}').format(self.b)
        return sa + '=>' + sb


class EstForm(Form):
    def __init__(self, expr: Form, cmpsign, est: float):
        self.expr = expr
        if cmpsign in ['<=', '<', '>', '>=']:
            self.cmpsign = cmpsign
        else:
            raise ValueError()
        if est >= 0 and est <= 1:
            self.est = est
        else:
            raise ValueError()

    def __repr__(self):
        return '{}{}{}'.format(str(self.expr), self.cmpsign, self.est)


class SignedForm(Form):
    def __init__(self, expr, sign='+'):
        if sign in ['-', '+']:
            self.positive = sign == '+'
        else:
            raise ValueError()
        self.expr = expr

    def __repr__(self):
        return '{}{}'.format('+' if self.positive else '-', self.expr)


parser = PEG('start',
             {
                 'atom': '[a-zA-Z][0-9a-zA-Z]*',
                 'estval': r'1|0(\.[0-9]*)?',
                 'ops': '[(]',
                 'cls': '[)]',
                 'neg': '~',
                 'disj': r'\|',
                 'conj': r'&',
                 'impl': r'=>',
                 'sign': r'\+|-',
                 'cmpsign': '<=|>=|<|>'
             },
             {
                 'prop': sel('propimp', 'propdis'),
                 'propimp': ['propdis', 'impl', 'propdis'],
                 'propdis': ['propcon', zom(['disj', 'propcon'])],
                 'propcon': ['atomicprop', zom(['conj', 'atomicprop'])],
                 'atomicprop': sel('atom', ['neg', 'atomicprop'], ['ops', 'prop', 'cls']),
                 'estprop': ['prop', 'cmpsign', 'estval'],
                 'estlog': sel('estimp', 'estdis'),
                 'estimp': ['estdis', 'impl', 'estdis'],
                 'estdis': ['estcon', zom(['disj', 'estcon'])],
                 'estcon': ['estatomic', zom(['conj', 'estatomic'])],
                 'estatomic': sel('estprop', ['neg', 'estatomic'], ['ops', 'estlog', 'cls']),
                 'start': [opt('sign'), 'estlog']
             }
             )


def syn2ast(node: TNode):
    if len(node.childs) == 2 and node.childs[1].symbol == 'zom':
        sym = 'con' if node.symbol in ['propcon', 'estcon'] else 'dis'
        res = TNode(sym)
        res.add(syn2ast(node.childs[0]))
        for sq in node.childs[1].childs:
            if sq.symbol == 'seq':
                # for c in sq.childs:
                #     res.add(syn2ast(c))
                res.add(syn2ast(sq.childs[1]))
        return res
    elif node.symbol == 'seq' and len(node.childs) == 2 and \
            type(node.childs[0].symbol) is Token and \
            node.childs[0].symbol.type == 'neg':

        res = TNode(node.childs[0].symbol)
        res.add(syn2ast(node.childs[1]))
        return res
    elif node.symbol == 'seq' and len(node.childs) == 3 and \
            type(node.childs[0].symbol) is Token and \
            node.childs[0].symbol.type == 'ops':
        return syn2ast(node.childs[1])
    elif node.symbol in ['propimp', 'estimp']:
        a = syn2ast(node.childs[0])
        b = syn2ast(node.childs[2])
        res = TNode('imp')
        res.add(a)
        res.add(b)
        return res
    elif node.symbol == 'estprop':
        res = TNode(node.childs[1].symbol)
        res.add(syn2ast(node.childs[0]))
        res.add(node.childs[2])
        return res
    elif len(node.childs) > 0 and \
            type(node.childs[0].symbol) is Token and \
            node.childs[0].symbol.type == 'sign':
        res = TNode(node.childs[0].symbol)
        for c in node.childs[1:]:
            res.add(syn2ast(c))
        return res
    elif len(node.childs) == 1:
        return syn2ast(node.childs[0])
    else:
        res = TNode(node.symbol)
        for c in node.childs:
            res.add(syn2ast(c))
        return res


def compile_ast(node):
    if type(node.symbol) is Token and node.symbol.type == 'sign':
        return SignedForm(compile_ast(node.childs[0]), node.symbol.value)
    elif type(node.symbol) is Token and node.symbol.type == 'cmpsign':
        return EstForm(
            compile_ast(node.childs[0]),
            node.symbol.value,
            float(node.childs[1].symbol.value))
    elif type(node.symbol) is Token and node.symbol.type == 'atom':
        return AtomForm(node.symbol.value)
    elif node.symbol == 'imp':
        return ImpForm(compile_ast(node.childs[0]), compile_ast(node.childs[1]))
    elif node.symbol == 'con':
        return ConForm([compile_ast(c) for c in node.childs])
    elif node.symbol == 'dis':
        return DisForm([compile_ast(c) for c in node.childs])
    elif type(node.symbol) is Token and node.symbol.type == 'neg':
        return NegForm(compile_ast(node.childs[0]))
    return ConForm([])


if __name__ == '__main__':
    from time import time

    s = 0


    def test(l):
        global s

        print('=' * 80)
        print('=' * 40)
        print(l)
        t = time()
        syntree = parser.Parse(l)
        s += time() - t
        #syntree.TreeRepr()
        print('=' * 40)
        print(l)
        ast = syn2ast(syntree)
        ast.TreeRepr()
        res = compile_ast(ast)
        print(res)
    N=1000
    for i in range(N):
        test('+p1>=0.7')
        test('q1=>p1&p2&~p3>=0.8')
        test('a&b&c&d&e>0.1')
        test('p1&~~p4=>q1>=0.9')
        test('~q2|q3>=0.6=>p1>=0.7')
        test('~(p1&q3=>~p2<=0.5)=>(p2&~q2>0.9)')

    print(s/N)
