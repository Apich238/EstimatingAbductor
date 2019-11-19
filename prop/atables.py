from prop import *


def consistent_join(liters, newlitera):
    nr = newlitera.reduce()
    if type(nr) is AtomForm or type(nr) is NegForm:
        nn = NegForm(newlitera).reduce()
        # nr = newlitera.reduce()
        for l in liters:
            # print('cmp',l,nn)
            if str(l) == str(nn):
                return None
            if str(l) == str(nr):
                return liters
        return liters + [nr]
    elif type(nr) is ConForm:
        res = liters.copy()
        for a in newlitera.members:
            res = consistent_join(res, a)
            if res is None:
                break
        return res
    else:
        raise ValueError()


def atables_open_branches(formulas, liters=[]):
    def select_formula(formulas: list):
        if len(formulas) == 0:
            return None
        for i, f in enumerate(formulas):
            if type(f) is AtomForm or type(f) is NegForm and type(f.value) is AtomForm:
                return i
        for i, f in enumerate(formulas):
            if type(f) is ConForm:
                return i
        for i, f in enumerate(formulas):
            if type(f) is DisForm:
                return i
        return 0

    if len(formulas) == 0:
        return [liters]
    res = []
    locfs = formulas.copy()
    fi = select_formula(locfs)
    f = locfs[fi]
    locfs.pop(fi)
    # print('f:', f, 'forms:', locfs, 'lits:', liters)
    if type(f) is ConForm:
        res = atables_open_branches(f.members + locfs, liters)
    elif type(f) is AtomForm:
        j = consistent_join(liters, f)
        if not j is None:
            res.extend(atables_open_branches(locfs, j))
        else:
            return []
    elif type(f) is DisForm:
        for m in f.members:
            res.extend(atables_open_branches([m] + locfs, liters))
    elif type(f) is NegForm:
        sf = f.reduce()
        if type(sf) is AtomForm or type(sf) is NegForm and type(sf.value) is AtomForm:
            j = consistent_join(liters, sf)
            if not j is None:
                res.extend(atables_open_branches(locfs, j))
            else:
                return []
        else:
            return atables_open_branches([sf] + locfs, liters)
    else:
        return []
    # print('res:', res)
    return res


def litera_not_cover(branches, litera):
    res = []
    for l in branches:
        r = consistent_join(l, litera)
        if r is None:
            res.append(l)
    return res


def filter(branches, liters):
    res = branches.copy()
    for l in liters:
        res = litera_not_cover(res, l)
        if len(res) == 0:
            break
    return res


# переборный метод преобразования бз
def KB2DNF(rs: list):
    # print('rs={}'.format(rs))
    if len(rs)==0:
        return []
    elif len(rs) == 1:
        if type(rs[0]) is DisForm:
            return [consistent_join([], a) for a in rs[0].members]
        else:
            return [[rs[0]]]
    res = []
    a = rs[0]
    rst = KB2DNF(rs[1:])
    # print('deb a={} rst={}'.format(a, rst))
    if type(a) is DisForm:
        variants = a.members
    else:
        variants = [a]
    for v in variants:
        sv = v.reduce()
        for r in rst:
            c = consistent_join(r, sv)
            if not c is None:
                res.append(c)
    return res


def build_graph(P, C, Q):
    cs={i:c for i,c in enumerate(C)}
    ps={a:[] for a in P}
    qs={a:[] for a in Q}
    for i,br in enumerate(C):
        for p in P:
            if NegForm(p) in br:
                ps[p].append(i)
        for q in Q:
            if NegForm(q) in br:
                qs[q].append(i)
    return cs,ps,qs


def simplify(kb: list):
    def is_strong_subset(a, b):
        f = True
        for ae in a:
            f = ae in b
            if not f: break
        return f and len(a) < len(b)

    def minimal(f, kb):
        fl = True
        for f2 in kb:
            fl = not is_strong_subset(f2, f)
            if not fl: break
        return fl

    res = []
    # kb = kb.copy()
    # while len(kb) > 0:
    #     cand = kb.pop(0)
    #     if minimal(cand, kb):
    #         res.append(cand)
    for cand in kb:
        if minimal(cand, kb):
            res.append(cand)
    return res
