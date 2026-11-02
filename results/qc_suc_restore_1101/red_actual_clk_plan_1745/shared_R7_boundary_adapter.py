def model_x(P, libs, r, c, wire_cls, ffc=H.FFC):
    """R6 model() with per-wire (r,c) by edge level and arbitrary masters.  wire_cls[l] in {'std','ndr2w'} for l=1..depth."""
    mz = P['mz']; nodes = P['nodes']; ch = collections.defaultdict(list)
    for n in nodes:
        if n[1]: ch[n[1]].append(n)
    pos = {n[0]: mz.xy(n[2]) for n in nodes}; mst = {n[0]: n[3] for n in nodes}
    wirelen = {}
    for w in P['wires']:
        e = w['edge']; segs = w['segs']
        names = [e + '_br'] + [e + '_r%d' % i for i in range(len(segs) - 1)] + [e]
        for i in range(len(segs)): wirelen[names[i + 1]] = segs[i]
    pos_hub = {w['edge']: mz.xy(w['cells'][-1][-1]) for w in P['wires']}
    def rc(l):
        return (r * NDR_R, c * NDR_C) if wire_cls.get(l, 'std') == 'ndr2w' else (r, c)
    res = {}; stage = {}; P['_int'] = {}
    for corner, L in libs.items():
        scap = P.get('sinkcap', {}).get(corner, {})
        arr = {'root': P.get('input_arrival_ps',0.0)}; slew = {'root': P.get('input_slew_ps',0.0)}; leafarr = {}; cd = {}; drv = {}
        stack = ['root']
        while stack:
            u = stack.pop(); kids = ch.get(u, []); lib = L[mst[u]]
            if kids and u in P['land']:
                seg, hub = P['land'][u]; hp = pos_hub[hub]; rr, cc = rc(lvl_of(hub))
                stub = [abs(pos[k[0]][0] - hp[0]) + abs(pos[k[0]][1] - hp[1]) for k in kids]
                Cl = sum(L[k[3]]['cin'] for k in kids) + cc * sum(stub); Ct = cc * seg + Cl
                d = 0.5 * (H.interp(lib['rise'], slew[u], Ct) + H.interp(lib['fall'], slew[u], Ct))
                so = 0.5 * (H.interp(lib['trise'], slew[u], Ct) + H.interp(lib['tfall'], slew[u], Ct))
                el = rr * seg * (cc * seg / 2 + Cl)
                drv[u] = (Ct, [(k[0], el + rr * sl_ * L[k[3]]['cin']) for k, sl_ in zip(kids, stub)])
                for k, sl_ in zip(kids, stub):
                    e2 = el + rr * sl_ * L[k[3]]['cin']
                    arr[k[0]] = arr[u] + d + e2; slew[k[0]] = math.hypot(so, 2.2 * e2); stack.append(k[0])
                    cd[k[0]] = (round(d, 2), round(e2, 2), round(so, 1))
                kids = []
            if kids:
                br = []
                for k in kids:
                    w = wirelen.get(k[0], abs(pos[k[0]][0] - pos[u][0]) + abs(pos[k[0]][1] - pos[u][1]))
                    br.append((w, L[k[3]]['cin'], rc(lvl_of(k[0]))))
                far = [b for b in br if b[0] >= 3.0]
                if len(far) > 1: raise ValueError('shared wire at ' + u)
                Ct = sum(b[2][1] * b[0] + b[1] for b in br)
                d = 0.5 * (H.interp(lib['rise'], slew[u], Ct) + H.interp(lib['fall'], slew[u], Ct))
                so = 0.5 * (H.interp(lib['trise'], slew[u], Ct) + H.interp(lib['tfall'], slew[u], Ct))
                drv[u] = (Ct, [(k[0], rr * w * (cc * w / 2 + cp)) for (w, cp, (rr, cc)), k in zip(br, kids)])
                for (w, cp, (rr, cc)), k in zip(br, kids):
                    el = rr * w * (cc * w / 2 + cp)
                    arr[k[0]] = arr[u] + d + el; slew[k[0]] = math.hypot(so, 2.2 * el); stack.append(k[0])
                    cd[k[0]] = (round(d, 2), round(el, 2), round(so, 1))
            if u in P['leafsinks']:
                ls = P['leafsinks'][u]; pts = [pos[u]] + [s[:2] for s in ls]
                par, order = H.mst_edges(pts); sub = [0.0] + [scap.get('%s/%s' % (q[2], q[3]), ffc[corner]) for q in ls]; ec = [0.0] * len(pts); er = [0.0] * len(pts)
                lr, lc = (r * NDR_R, c * NDR_C) if LEAF_NDR else (r, c)
                for v in order[1:]:
                    e = abs(pts[v][0] - pts[par[v]][0]) + abs(pts[v][1] - pts[par[v]][1]); ec[v] = lc * e; er[v] = lr * e
                for v in reversed(order[1:]): sub[par[v]] += sub[v] + ec[v]
                Ct = sub[0]
                d = 0.5 * (H.interp(lib['rise'], slew[u], Ct) + H.interp(lib['fall'], slew[u], Ct))
                so = 0.5 * (H.interp(lib['trise'], slew[u], Ct) + H.interp(lib['tfall'], slew[u], Ct))
                t = [0.0] * len(pts)
                for v in order[1:]: t[v] = t[par[v]] + er[v] * (sub[v] - ec[v] / 2)
                vals = [arr[u] + d + x for x in t[1:]]
                drv[u] = (Ct, [('#sinks', sum(t[1:]) / len(ls))])
                leafarr[u] = (sum(vals) / len(vals), min(vals), max(vals), Ct, d, so, slew[u])
        P['_int'][corner] = dict(arr=dict(arr), slew=dict(slew), drv=drv)
        means = [v[0] for v in leafarr.values()]; allv = []
        for u, v in leafarr.items(): allv += [v[1], v[2]]
        n_s = sum(len(P['leafsinks'][u]) for u in leafarr)
        mean = sum(leafarr[u][0] * len(P['leafsinks'][u]) for u in leafarr) / n_s
        res[corner] = dict(mean=round(mean, 2), leaf_mean_min=round(min(means), 2), leaf_mean_max=round(max(means), 2),
                           window=round(max(means) - min(means), 2), sink_min=round(min(allv), 2), sink_max=round(max(allv), 2),
                           leaf_slew_in_max=round(max(v[6] for v in leafarr.values()), 1),
                           leaf_ct_ff=[round(min(v[3] for v in leafarr.values()), 1), round(max(v[3] for v in leafarr.values()), 1)],
                           leaf_out_slew_max=round(max(v[5] for v in leafarr.values()), 1))
        # stage breakdown along the worst (latest) leaf path
        worst = max(leafarr, key=lambda u: leafarr[u][0]); path = []; par_ = {n[0]: n[1] for n in nodes}; u = worst
        while par_[u]: path.append((u, mst[par_[u]]) + cd.get(u, ())); u = par_[u]
        stage[corner] = dict(leaf=worst, leaf_drv=[round(leafarr[worst][4], 2), round(leafarr[worst][0] - arr[worst] - leafarr[worst][4], 2)],
                             path=list(reversed(path)))
    return res, stage
