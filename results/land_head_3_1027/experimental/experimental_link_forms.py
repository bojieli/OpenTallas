

# delay model of one buffered leg (BUF at the far node, BUFx repeaters every rep_um): least-squares fit of LAND-HEAD-1 sl300
# GRT-RC routed die-clock stage delays (TT, landed_topo_model.fit): a + b1*s + b2*s^2 per stage, + f per extra sibling.
LINK_DME_STAGE = (23.96, 0.1382, 0.000331, 20.46)


def _leg_ps(L, rep_um=450.0, fan=2):
    a, b1, b2, f = LINK_DME_STAGE
    n = max(1, int(math.ceil(L / rep_um)))
    s = L / n
    return n * (a + b1 * s + b2 * s * s) + f * (fan - 1)


def build_link_dme(P, taps, rep_um=450.0):
    """LAND-HEAD-3 (opt-in --tree-form link_dme, METHODOLOGY 12.13b 'clock follows data'): the die clock is a zero-skew
    tree whose TOPOLOGY is the plan's crossing (link) graph.  Each partition's clock entry is a leaf driven by a buffer AT the
    entry.  Clusters are merged bottom-up, only along links (two clusters merge only if a crossing joins them), always the
    adjacent pair whose merged insertion is smallest; the merge point is the delay-balanced (DME) point on the Manhattan path
    between the two sub-roots (delay = stage model above), so every landed pair diverges at the first merge that joins its
    two partitions -- neighbours split late, far partitions never carry a crossing.  An unbalanced pair that cannot be
    balanced on the path gets a detour node on the shorter side (length reported as detour_um; no padding cells)."""
    import heapq
    part_xy = {}
    for t in taps:
        part_xy.setdefault(t[0], []).append(t)
    adj = defaultdict(lambda: defaultdict(int))
    for pr in P.raw["ports"]:
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if a != b and a in part_xy and b in part_xy:
            adj[a][b] += int(pr.get("width", 1))
            adj[b][a] += int(pr.get("width", 1))
    # cluster: (x, y, t_ps, struct); struct = ("leaf", part) | ("m", (x,y), s1, s2, detour)
    C = {}
    for n, tl in part_xy.items():
        x = sum(t[2] for t in tl) / len(tl)
        y = sum(t[3] for t in tl) / len(tl)
        C[n] = (x, y, 0.0, ("leaf", n))
    cadj = {n: set(adj[n]) for n in C}
    detour_tot = [0.0]

    def merge(c1, c2):
        x1, y1, t1, s1 = c1
        x2, y2, t2, s2 = c2
        D = abs(x1 - x2) + abs(y1 - y2)

        def at(d):            # point at Manhattan distance d from (x1,y1) along horizontal-then-vertical path
            hx = abs(x2 - x1)
            if d <= hx:
                return (x1 + math.copysign(d, x2 - x1), y1)
            return (x2, y1 + math.copysign(d - hx, y2 - y1))
        f = lambda d: (t1 + (_leg_ps(d, rep_um) if d > 1e-6 else 0.0)) - (t2 + (_leg_ps(D - d, rep_um) if D - d > 1e-6 else 0.0))
        if f(0.0) <= 0 <= f(D):
            lo, hi = 0.0, D
            for _ in range(60):
                mid = (lo + hi) / 2
                (lo, hi) = (mid, hi) if f(mid) < 0 else (lo, mid)
            d = (lo + hi) / 2
            mx, my = at(d)
            t = max(t1 + (_leg_ps(d, rep_um) if d > 1e-6 else 0.0), t2 + (_leg_ps(D - d, rep_um) if D - d > 1e-6 else 0.0))
            return (mx, my, t, ("m", (mx, my), s1, s2, 0.0, 0.0))
        # cannot balance on the path: merge at the deeper root, detour leg (length Le >= D) to the shallower one
        if f(0.0) > 0:     # c1 deeper
            deep, sh, tdeep, tsh, (mx, my), first = s1, s2, t1, t2, (x1, y1), True
        else:
            deep, sh, tdeep, tsh, (mx, my), first = s2, s1, t2, t1, (x2, y2), False
        lo, hi = D, D + 20000.0
        for _ in range(60):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if tsh + _leg_ps(mid, rep_um) < tdeep else (lo, mid)
        Le = lo
        det = Le - D
        detour_tot[0] += det
        t = max(tdeep, tsh + _leg_ps(Le, rep_um))
        return (mx, my, t, ("m", (mx, my), deep, sh, 0.0, det) if first else ("m", (mx, my), sh, deep, det, 0.0))

    ver = {n: 0 for n in C}
    h = []

    def push(a, b):
        m = merge(C[a], C[b])
        heapq.heappush(h, (m[2], a, b, ver[a], ver[b]))
    for a in C:
        for b in cadj[a]:
            if a < b:
                push(a, b)
    k = 0
    while len(C) > 1:
        if not h:   # disconnected link graph: join the two nearest clusters
            ks = sorted(C)
            a, b = min(((p, q) for i, p in enumerate(ks) for q in ks[i + 1:]),
                       key=lambda pq: abs(C[pq[0]][0] - C[pq[1]][0]) + abs(C[pq[0]][1] - C[pq[1]][1]))
            cadj[a].add(b)
            cadj[b].add(a)
            push(a, b)
            continue
        t, a, b, va, vb = heapq.heappop(h)
        if a not in C or b not in C or ver[a] != va or ver[b] != vb:
            continue
        m = merge(C[a], C[b])
        k += 1
        new = f"__m{k}"
        C[new] = m
        ver[new] = 0
        nb = (cadj.pop(a) | cadj.pop(b)) - {a, b}
        del C[a], C[b]
        cadj[new] = nb
        for c in nb:
            cadj[c] -= {a, b}
            cadj[c].add(new)
            push(*sorted((new, c)))
    (rx, ry, rt, rs), = C.values()
    nodes = {}

    def mk(x, y, parent, level, **kw):
        i = len(nodes)
        nodes[i] = dict(id=i, x=round(x, 3), y=round(y, 3), parent=parent, level=level, kids=[], taps=[],
                        region=[0.0, 0.0, P.W, P.H], **kw)
        if parent is not None:
            nodes[parent]["kids"].append(i)
        return i
    stack = [(rs, None, 0, 0.0)]
    while stack:
        s, parent, level, det = stack.pop()
        par = parent
        if det > 1e-6 and parent is not None:     # detour: a node offset perpendicular so the leg is det longer
            px, py = nodes[parent]["x"], nodes[parent]["y"]
            cx, cy = (s[1] if s[0] == "m" else (sum(t[2] for t in part_xy[s[1]]) / len(part_xy[s[1]]),
                                                 sum(t[3] for t in part_xy[s[1]]) / len(part_xy[s[1]])))
            vertical = abs(cx - px) >= abs(cy - py)
            off = det / 2
            qx, qy = ((px, py + off if py + off < P.H else py - off) if vertical else
                      (px + off if px + off < P.W else px - off, py))
            par = mk(qx, qy, parent, level, detour_um=round(det, 1))
            level += 1
        if s[0] == "leaf":
            tl = part_xy[s[1]]
            x = sum(t[2] for t in tl) / len(tl)
            y = sum(t[3] for t in tl) / len(tl)
            i = mk(x, y, par, level, part=s[1])
            nodes[i]["taps"] += tl
        else:
            _, (mx, my), s1, s2, d1, d2 = s
            i = mk(mx, my, par, level, link_merge=True)
            stack.append((s2, i, level + 1, d2))
            stack.append((s1, i, level + 1, d1))
    nodes[0]["link_dme"] = dict(merges=k, model_insertion_ps=round(rt, 1), detour_um=round(detour_tot[0], 1),
                                stage_model=list(LINK_DME_STAGE))
    return nodes



def build_link_xdme(P, taps, rep_um=450.0, p_frac=0.078, p0_ps=40.0, max_detour_um=3000.0):
    """LAND-HEAD-3 (opt-in --tree-form link_xdme, METHODOLOGY 12.13b 'clock follows data', CROSSING-AWARE): like link_dme
    the tree is merged bottom-up only along links, but it is NOT zero-skew.  At every merge only the crossings CUT by that
    merge matter (their LCA is this merge point), so the merge point (on the Manhattan path between the two sub-roots,
    or a detour leg <= max_detour_um on one side) is chosen to minimise, over the cut crossings, the estimated phase need
    |d| + p_frac * max(unshared) + p0_ps (d, unshared from the stage model; p_frac/p0 approximate the shared AOCV+droop
    pessimism).  The adjacent cluster pair with the smallest need merges first.  Far partitions may differ by many ns:
    only linked pairs are balanced, so insertion is not equalised die-wide (no deep die tree).  The gate is
    landed_phase_ocv on routed arrivals, not this estimate."""
    import heapq
    part_xy = {}
    for t in taps:
        part_xy.setdefault(t[0], []).append(t)
    adj = defaultdict(set)
    for pr in P.raw["ports"]:
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if a != b and a in part_xy and b in part_xy:
            adj[a].add(b)
            adj[b].add(a)
    cen = {n: (sum(t[2] for t in tl) / len(tl), sum(t[3] for t in tl) / len(tl)) for n, tl in part_xy.items()}
    # cluster: dict(x, y, lat{part: ps below root}, s=struct)
    C = {n: dict(x=cen[n][0], y=cen[n][1], lat={n: 0.0}, s=("leaf", n)) for n in part_xy}
    owner = {n: n for n in part_xy}
    cadj = {n: set(adj[n]) for n in C}
    lg = lambda L: _leg_ps(L, rep_um) if L > 1e-6 else 0.0

    def cut(A, B):
        a_, b_ = (A, B) if len(C[A]["lat"]) <= len(C[B]["lat"]) else (B, A)
        out = [(p, q) for p in C[a_]["lat"] for q in adj[p] if owner[q] == b_]
        return [(p, q) if a_ == A else (q, p) for p, q in out]   # (part in A, part in B)

    def plan_merge(A, B):
        ca, cb = C[A], C[B]
        D = abs(ca["x"] - cb["x"]) + abs(ca["y"] - cb["y"])
        pairs = cut(A, B)
        la = [ca["lat"][p] for p, _ in pairs]
        lb = [cb["lat"][q] for _, q in pairs]

        def need(ea, eb):     # ea/eb: leg length to A/B root
            da, db = lg(ea), lg(eb)
            return max(abs((db + y) - (da + x)) + p_frac * max(da + x, db + y) + p0_ps for x, y in zip(la, lb))
        cands = [(need(D * f, D * (1 - f)), D * f, 0.0, 0.0) for f in [i / 40 for i in range(41)]]
        for e in [D + max_detour_um * i / 12 for i in range(1, 13)]:
            cands.append((need(e, 0.0), 0.0, e - D, 0.0) if True else None)
            cands.append((need(0.0, e), D, 0.0, e - D))
        best = min(cands)
        return best   # (need, x along path from A root, detourA, detourB)

    def at(ca, cb, d):
        x1, y1, x2, y2 = ca["x"], ca["y"], cb["x"], cb["y"]
        hx = abs(x2 - x1)
        if d <= hx:
            return (x1 + math.copysign(d, x2 - x1), y1)
        return (x2, y1 + math.copysign(min(d - hx, abs(y2 - y1)), y2 - y1))
    h = []
    ver = {n: 0 for n in C}

    def push(a, b):
        nd = plan_merge(a, b)
        heapq.heappush(h, (nd[0], a, b, ver[a], ver[b]))
    for a in C:
        for b in cadj[a]:
            if a < b:
                push(a, b)
    k = 0
    worst_need = 0.0
    while len(C) > 1:
        if not h:
            ks = sorted(C)
            a, b = min(((p, q) for i, p in enumerate(ks) for q in ks[i + 1:]),
                       key=lambda pq: abs(C[pq[0]]["x"] - C[pq[1]]["x"]) + abs(C[pq[0]]["y"] - C[pq[1]]["y"]))
            cadj[a].add(b)
            cadj[b].add(a)
            push(a, b)
            continue
        _, a, b, va, vb = heapq.heappop(h)
        if a not in C or b not in C or ver[a] != va or ver[b] != vb:
            continue
        nd, x, detA, detB = plan_merge(a, b)
        worst_need = max(worst_need, nd)
        ca, cb = C[a], C[b]
        D = abs(ca["x"] - cb["x"]) + abs(ca["y"] - cb["y"])
        mx, my = at(ca, cb, x)
        eA, eB = x + detA, (D - x) + detB
        lat = {p: lg(eA) + v for p, v in ca["lat"].items()}
        lat.update({p: lg(eB) + v for p, v in cb["lat"].items()})
        k += 1
        new = f"__x{k}"
        C[new] = dict(x=mx, y=my, lat=lat, s=("m", (mx, my), ca["s"], cb["s"], detA, detB))
        for p in lat:
            owner[p] = new
        ver[new] = 0
        nb = (cadj.pop(a) | cadj.pop(b)) - {a, b}
        del C[a], C[b]
        cadj[new] = nb
        for c in nb:
            cadj[c] -= {a, b}
            cadj[c].add(new)
            push(*sorted((new, c)))
    (root,) = C.values()
    nodes = {}
    detour_tot = 0.0

    def mk(x, y, parent, level, **kw):
        i = len(nodes)
        nodes[i] = dict(id=i, x=round(x, 3), y=round(y, 3), parent=parent, level=level, kids=[], taps=[],
                        region=[0.0, 0.0, P.W, P.H], **kw)
        if parent is not None:
            nodes[parent]["kids"].append(i)
        return i
    stack = [(root["s"], None, 0, 0.0)]
    while stack:
        s, parent, level, det = stack.pop()
        par = parent
        if det > 1e-6 and parent is not None:   # detour leg: one node offset so the leg is det longer (no padding cell)
            px, py = nodes[parent]["x"], nodes[parent]["y"]
            cx, cy = s[1] if s[0] == "m" else cen[s[1]]
            off = det / 2
            if abs(cx - px) >= abs(cy - py):
                qx, qy = px, (py + off if py + off < P.H else py - off)
            else:
                qx, qy = (px + off if px + off < P.W else px - off), py
            par = mk(qx, qy, parent, level, detour_um=round(det, 1))
            detour_tot += det
            level += 1
        if s[0] == "leaf":
            i = mk(*cen[s[1]], par, level, part=s[1])
            nodes[i]["taps"] += part_xy[s[1]]
        else:
            _, (mx, my), s1, s2, d1, d2 = s
            i = mk(mx, my, par, level, link_merge=True)
            stack.append((s2, i, level + 1, d2))
            stack.append((s1, i, level + 1, d1))
    nodes[0]["link_dme"] = dict(form="crossing_aware", merges=k, model_worst_need_ps=round(worst_need, 1),
                                model_insertion_max_ps=round(max(root["lat"].values()), 1),
                                model_insertion_min_ps=round(min(root["lat"].values()), 1), detour_um=round(detour_tot, 1),
                                stage_model=list(LINK_DME_STAGE), p_frac=p_frac, p0_ps=p0_ps)
    return nodes



def build_link_forward(P, taps, rep_um=450.0, cap_ps=1300.0, near_um=1100.0, p_frac=0.078, p0_ps=40.0,
                       max_detour_um=3000.0):
    """LAND-HEAD-3 (opt-in --tree-form link_forward, METHODOLOGY 12.13a/b): REGION clocks that FOLLOW THE DATA.
    (1) Regions: partitions are merged bottom-up into zero-skew (DME, stage model above) local trees, only between clusters
        joined by a link or lying within near_um of each other, smallest merged insertion first, while the local insertion
        stays <= cap_ps (shallow region clock, 12.13a guidance ~1-1.5 ns).
    (2) Feed: the region graph (regions joined by crossings) is walked breadth-first from its graph centre; every region is
        fed from an already clocked NEIGHBOUR region it has crossings with (the one with most crossings), by one leg from the
        node of that neighbour's tree that best balances the crossings between them (|d| + p_frac*unshared + p0, the
        shared-model estimate; detour leg <= max_detour_um allowed).  So each crossing's two branches diverge inside the
        neighbour pair (unshared ~ local insertion + one leg), never at a die-wide root; insertion grows along the feed
        graph but only linked pairs are balanced.  Non-feed region edges (loops in the region graph) are reported.
    The gate is landed_phase_ocv on routed arrivals."""
    import heapq
    part_xy = {}
    for t in taps:
        part_xy.setdefault(t[0], []).append(t)
    adj = defaultdict(lambda: defaultdict(int))
    for pr in P.raw["ports"]:
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if a != b and a in part_xy and b in part_xy:
            adj[a][b] += 1
            adj[b][a] += 1
    cen = {n: (sum(t[2] for t in tl) / len(tl), sum(t[3] for t in tl) / len(tl)) for n, tl in part_xy.items()}
    lg = lambda L: _leg_ps(L, rep_um) if L > 1e-6 else 0.0
    M = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])

    # ---- (1) regions: zero-skew agglomeration under the insertion cap
    C = {n: dict(x=cen[n][0], y=cen[n][1], t=0.0, s=("leaf", n), mem={n}) for n in part_xy}
    names = sorted(part_xy)
    near = defaultdict(set)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if b in adj[a] or M(cen[a], cen[b]) <= near_um:
                near[a].add(b)
                near[b].add(a)
    cadj = {n: set(near[n]) for n in C}
    ladj = {n: set(adj[n]) for n in C}          # LINK adjacency between clusters

    def mergeable(a, b):     # linked, or near AND sharing a linked neighbour (merging then adds no region-graph loop)
        return b in ladj[a] or bool(ladj[a] & ladj[b])

    def zmerge(c1, c2):
        x1, y1, t1 = c1["x"], c1["y"], c1["t"]
        x2, y2, t2 = c2["x"], c2["y"], c2["t"]
        D = abs(x1 - x2) + abs(y1 - y2)

        def at(d):
            hx = abs(x2 - x1)
            return (x1 + math.copysign(d, x2 - x1), y1) if d <= hx else (x2, y1 + math.copysign(d - hx, y2 - y1))
        f = lambda d: (t1 + lg(d)) - (t2 + lg(D - d))
        if f(0.0) <= 0 <= f(D):
            lo, hi = 0.0, D
            for _ in range(50):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
            d = (lo + hi) / 2
            mx, my = at(d)
            return dict(x=mx, y=my, t=max(t1 + lg(d), t2 + lg(D - d)), s=("m", (mx, my), c1["s"], c2["s"], 0.0, 0.0),
                        mem=c1["mem"] | c2["mem"])
        return None                 # not balanceable on the path: never merged into one region
    h, ver, k = [], {n: 0 for n in C}, 0

    def push(a, b):
        m = zmerge(C[a], C[b]) if mergeable(a, b) else None
        if m is not None and m["t"] <= cap_ps:
            heapq.heappush(h, (m["t"], a, b, ver[a], ver[b]))
    for a in C:
        for b in cadj[a]:
            if a < b:
                push(a, b)
    while h:
        _, a, b, va, vb = heapq.heappop(h)
        if a not in C or b not in C or ver[a] != va or ver[b] != vb or not mergeable(a, b):
            continue
        k += 1
        new = f"__r{k}"
        C[new] = zmerge(C[a], C[b])
        ver[new] = 0
        lb = (ladj.pop(a) | ladj.pop(b)) - {a, b}
        ladj[new] = lb
        for c in lb:
            ladj[c] -= {a, b}
            ladj[c].add(new)
        nb = (cadj.pop(a) | cadj.pop(b) | lb) - {a, b}
        del C[a], C[b]
        cadj[new] = nb
        for c in nb:
            cadj[c] -= {a, b}
            cadj[c].add(new)
        for c in set(cadj[new]) | {x for y in lb for x in ladj[y]} - {new}:
            if c in C and c != new:
                push(*sorted((new, c)))
    regions = sorted(C, key=lambda r: (-len(C[r]["mem"]), min(C[r]["mem"])))
    reg_of = {p: r for r in regions for p in C[r]["mem"]}

    # ---- global node list; each region's local tree is expanded when it is fed
    nodes = {}

    def mk(x, y, parent, **kw):
        i = len(nodes)
        lvl = 0 if parent is None else nodes[parent]["level"] + 1
        nodes[i] = dict(id=i, x=round(x, 3), y=round(y, 3), parent=parent, level=lvl, kids=[], taps=[],
                        region=[0.0, 0.0, P.W, P.H], **kw)
        if parent is not None:
            nodes[parent]["kids"].append(i)
        return i
    lat = {}                    # node id -> model latency from the die root (ps)
    part_node = {}

    def expand(r, parent, t0):
        """expand region r's local zero-skew tree below node `parent` (whose latency is t0); returns its root node."""
        def rec(s, par, tpar):
            pos = s[1] if s[0] == "m" else cen[s[1]]
            t = tpar + (lg(M(pos, (nodes[par]["x"], nodes[par]["y"]))) if par is not None else 0.0)
            i = mk(pos[0], pos[1], par, clock_region=r, **({"part": s[1]} if s[0] == "leaf" else {}))
            lat[i] = t
            if s[0] == "leaf":
                nodes[i]["taps"] += part_xy[s[1]]
                part_node[s[1]] = i
            else:
                rec(s[2], i, t)
                rec(s[3], i, t)
            return i
        return rec(C[r]["s"], parent, t0)

    rgraph = defaultdict(lambda: defaultdict(int))
    for a in adj:
        for b, c in adj[a].items():
            if reg_of[a] != reg_of[b]:
                rgraph[reg_of[a]][reg_of[b]] += c

    def ecc(r0):
        seen, fr, d = {r0}, [r0], 0
        while fr:
            nx = [q for p in fr for q in rgraph[p] if q not in seen]
            seen.update(nx)
            fr, d = list(dict.fromkeys(nx)), d + (1 if nx else 0)
        return (len(seen) < len(regions), d)
    root_r = min(regions, key=lambda r: (ecc(r), M((C[r]["x"], C[r]["y"]), (P.W / 2, P.H / 2))))

    def anc(i):
        out = []
        while i is not None:
            out.append(i)
            i = nodes[i]["parent"]
        return out
    def loc_of(r):
        acc = {}

        def rec(s, t):
            pos = s[1] if s[0] == "m" else cen[s[1]]
            if s[0] == "leaf":
                acc[s[1]] = t
                return
            for ch in (s[2], s[3]):
                rec(ch, t + lg(M(pos, ch[1] if ch[0] == "m" else cen[ch[1]])))
        rec(C[r]["s"], 0.0)
        return acc
    fed = {root_r: None}
    worst0 = []
    if len(regions) > 1:    # TOP = one balanced merge of the centre region A and its heaviest neighbour B (crossing-aware)
        rb = max(rgraph[root_r], key=lambda r: (rgraph[root_r][r], r))
        la_, lb_ = loc_of(root_r), loc_of(rb)
        pairs0 = [(a, b) for a in C[root_r]["mem"] for b in adj[a] if reg_of[b] == rb]
        A0, B0 = (C[root_r]["x"], C[root_r]["y"]), (C[rb]["x"], C[rb]["y"])
        D0 = M(A0, B0)
        best0 = None
        for f in [i / 40 for i in range(41)]:
            ea, eb = D0 * f, D0 * (1 - f)
            nd = max(abs((lg(eb) + lb_[b]) - (lg(ea) + la_[a])) + p_frac * max(lg(eb) + lb_[b], lg(ea) + la_[a]) + p0_ps
                     for a, b in pairs0)
            if best0 is None or nd < best0[0]:
                best0 = (nd, f)
        f = best0[1]
        hx = abs(B0[0] - A0[0])
        dd = D0 * f
        mxy = (A0[0] + math.copysign(dd, B0[0] - A0[0]), A0[1]) if dd <= hx else             (B0[0], A0[1] + math.copysign(dd - hx, B0[1] - A0[1]))
        m0 = mk(mxy[0], mxy[1], None, clock_region="top")
        lat[m0] = 0.0
        expand(root_r, m0, 0.0)
        expand(rb, m0, 0.0)
        fed[rb] = (root_r, m0, round(best0[0], 1))
        worst0.append(best0[0])
    else:
        expand(root_r, None, 0.0)
    order = list(fed)
    worst = list(worst0)
    loops = 0
    q = list(fed)
    while q:
        nq = []
        for rp in q:
            for rc in sorted(rgraph[rp], key=lambda r: -rgraph[rp][r]):
                if rc in fed:
                    continue
                # choose feeding node in the clocked set: candidates = nodes of rp's local tree + its feed chain
                pairs = [(a, b) for b in C[rc]["mem"] for a in adj[b] if reg_of[a] in fed]
                rc_root = (C[rc]["x"], C[rc]["y"])
                loc = {}

                def loc_lat(s, t, acc):    # local latency of every part below rc root
                    pos = s[1] if s[0] == "m" else cen[s[1]]
                    if s[0] == "leaf":
                        acc[s[1]] = t
                        return
                    for ch in (s[2], s[3]):
                        cp = ch[1] if ch[0] == "m" else cen[ch[1]]
                        loc_lat(ch, t + lg(M(pos, cp)), acc)
                loc_lat(C[rc]["s"], 0.0, loc)
                cands = set()
                for a, _ in pairs:
                    cands.update(anc(part_node[a]))
                best = None
                for n in cands:
                    D = M((nodes[n]["x"], nodes[n]["y"]), rc_root)
                    an = set(anc(n))
                    for e in [D] + [D + max_detour_um * i / 8 for i in range(1, 9)]:
                        tq0 = lat[n] + lg(e)
                        need = 0.0
                        for a, b in pairs:
                            pa = part_node[a]
                            l_ = next(x for x in anc(pa) if x in an)
                            ua, ub = lat[pa] - lat[l_], tq0 + loc[b] - lat[l_]
                            dd = (tq0 + loc[b]) - lat[pa]
                            need = max(need, abs(dd) + p_frac * max(ua, ub) + p0_ps)
                        if best is None or need < best[0]:
                            best = (need, n, e, D)
                need, n, e, D = best
                par = n
                if e - D > 1e-6:
                    px, py = nodes[n]["x"], nodes[n]["y"]
                    off = (e - D) / 2
                    qx, qy = (px, py + off if py + off < P.H else py - off) if abs(rc_root[0] - px) >= abs(rc_root[1] - py) \
                        else (px + off if px + off < P.W else px - off, py)
                    par = mk(qx, qy, n, detour_um=round(e - D, 1), clock_region=rp)
                    lat[par] = lat[n] + lg(M((px, py), (qx, qy)))
                expand(rc, par, lat[par])
                fed[rc] = (rp, n, round(need, 1))
                worst.append(need)
                order.append(rc)
                nq.append(rc)
        q = nq
    assert len(fed) == len(regions), (len(fed), len(regions))
    for ra in rgraph:
        for rb in rgraph[ra]:
            if ra < rb and (fed.get(ra) or (None,))[0] != rb and (fed.get(rb) or (None,))[0] != ra:
                loops += 1
    nodes[0]["link_dme"] = dict(form="link_forward", regions=len(regions), region_sizes=sorted((len(C[r]["mem"]) for r in regions), reverse=True),
                                region_insertion_max_ps=round(max(C[r]["t"] for r in regions), 1), cap_ps=cap_ps, near_um=near_um,
                                root_region=sorted(C[root_r]["mem"])[:6], feed_edges=len(regions) - 1, loop_region_edges=loops,
                                model_worst_feed_need_ps=round(max(worst or [0]), 1),
                                model_insertion_max_ps=round(max(lat[part_node[p]] for p in part_node), 1),
                                stage_model=list(LINK_DME_STAGE), p_frac=p_frac, p0_ps=p0_ps)
    nodes[0]["region_feed"] = {sorted(C[r]["mem"])[0]: (sorted(C[v[0]]["mem"])[0], v[1], v[2]) for r, v in fed.items() if v}
    return nodes

