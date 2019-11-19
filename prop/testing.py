from atables import *


def parse_list(l: list, reduce=False):
    res = [AtomForm.Parse(s) for s in l]
    if reduce:
        res = [x.reduce() for x in res]
    return res


# print('======================================== ТЕСТ 1 ========================================')
# print('доказательство формулы методом аналитических таблиц')
# f = Form.Parse('((p=>(q=>r))=>((p=>q)=>(p=>r)))')
# ob = atables_open_branches([NegForm(f)])
# if len(ob) == 0:
#     print(f, 'общезначима')
# else:
#     print(f, 'противоречива')

def abduce_by_graph(graph, negobs, Abd):
    C, G1, G2 = graph
    tC = C.copy()
    for p in negobs:
        # print(p)
        # for i in tC:
        #     print('\t',tC[i])
        tC = {i: C[i] for i in tC if not i in G1[p]}
    # print('Формулы БЗ, не покрытые наблюдением:')
    # for i in tC: print('\t',i, tC[i])

    cands = []
    for i in tC:
        for q in Abd:
            if NegForm(q).reduce() in tC[i]:
                cands.append(NegForm(q).reduce())
    cands = list(set(cands))
    # print(cands)

    res = []

    def reccover(uncovered:dict,candidats:list):
        if len(uncovered)==0:
            return []
        if len(candidats)==0:
            return None
        res=[]
        for i in range(len(candidats)):
            c=candidats.copy()
            h=c.pop(i)
            #print('h,c ',h,c)
            new_uncovered={k:uncovered[k] for k in uncovered if not h in uncovered[k]}
            #print('uncov',new_uncovered)
            if len(new_uncovered)==0:
                res.append([h])
            else:
                res.extend([[h]+l for l in reccover(new_uncovered,c)])
        return res

    res=reccover(tC,cands)
    print('res',res)
    minres=simplify(res)
    print('minres',minres)

    # cands=[x for x in Abd if ]
    # hyps = []
    # print('Гипотезы:', hyps)
    # cw = {a: [x for x in skb2simp if not [NegForm(a).reduce(), x] in graph] for a in observation}
    # for a in cw: print('\t', a, cw[a])
    # for a in cw:
    #     l = cw[a]
    #     best = []
    #     candidats = abd.copy()
    #     score = len(l)  # сколько осталось покрыть
    #     print('a,l:', a, l)
    #     while score > 0:
    #         bestcand = None
    #         bestcandscore = score
    #         for c in candidats:
    #             newscore = len([x for x in l if NegForm(c).reduce() in x])
    #             if newscore < bestcandscore:
    #                 bestcand = c
    #                 bestcandscore = newscore
    #                 print('cand upd', c, bestcandscore)
    #         best.append(bestcand)
    #         score = bestcandscore
    #         l = [x for x in l if NegForm(bestcand).reduce() in x]
    #         print(score, best, l)
    return minres


def test_abduce(tkb, tobs):
    print('абдукция методом аналитических таблиц')
    kb = parse_list(tkb)
    print('база знаний: ', kb)
    observation = parse_list(tobs)
    print('Наблюдение:', observation)

    print('открытые ветви АТ БЗ (C):')
    skb1 = atables_open_branches(kb)
    for b in skb1: print('\t', b)
    print('открытые ветви АТ БЗ (C) с учётом поглощений:')
    skb1simp = simplify(skb1)
    for b in skb1simp: print('\t', b)

    print('дизъюнкты БЗ (C):')
    skb2 = KB2DNF([x.reduce() for x in kb])
    for b in skb2: print('\t', b)
    print('дизъюнкты БЗ (C) с учётом поглощений:')
    skb2simp = simplify(skb2)
    for b in skb2simp: print('\t', b)

    obs = parse_list(['p1', 'p2', 'p3'])
    obs.extend([NegForm(x) for x in obs])
    print('Атомы - наблюдения (P):', obs)
    abd = parse_list(['q1', 'q2', 'q3'])
    abd.extend([NegForm(x) for x in abd])
    print('Атомы - абдуценты (Q):', abd)

    graph = build_graph(obs, skb2simp, abd)
    print('Граф покрытий:')
    for e in graph: print('\t', e)

    print('Абдукция по графу')
    negobs = [NegForm(x) for x in observation]
    hyps = abduce_by_graph(graph, negobs, abd)
    print(hyps)
    
    return hyps


print('======================================== ТЕСТ 1 ========================================')
test_abduce(['q1=>p1&&p2&&!p3', 'p1&&p2&&!p3=>q1', 'q2=>p1&&p3', 'q3=>q2'], ['p1', 'p3'])

print('\n' * 2)
print('======================================== ТЕСТ 2 ========================================')
test_abduce(['q1=>p1&&p2&&!p3', 'p1&&p2&&!p3=>q1', 'q2=>p1&&p3', 'q3=>q2', 'q1||q2=>!q3'], ['p1', 'p3'])

print('\n' * 2)
print('======================================== ТЕСТ 3 ========================================')
test_abduce(['q1=>p1&&p2&&!p3', 'p1&&!p4=>q2', '!q2||q3=>!p4'], ['p1', 'p3'])
