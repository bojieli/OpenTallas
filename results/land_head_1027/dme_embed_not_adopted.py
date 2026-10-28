def dme_embed(nodes, site, step=0.54):
    """LAND-HEAD-1 10-27 (opt-in --tree-dme-legal): zero-skew path-length embedding (DME, Boese-Kahng/Chao) of the
    full-depth H-tree TOPOLOGY.  Leaves sit AT their single partition entry; bottom-up every branch node gets its
    merging segment (Manhattan arc, kept as a rectangle in u=x+y / v=x-y) on which both subtrees have equal root->entry
    wire length; top-down each node is placed on the LEGAL point of (its merging segment  /\\  the diamond of its edge
    length around the placed parent) nearest its ideal H-tree point.  Equal length is exact by construction (no slides,
    no meander); a node whose feasible set has no legal site is placed at the nearest legal site and reported
    (offset_um).  Corner nodes are dropped (L legs; repeaters on a monotone staircase keep the Manhattan length).
    Geometry only; no timing value is used.  Returns a report dict; nodes are edited in place."""
    def uv(p):
        return (p[0] + p[1], p[0] - p[1])

    def xy(q):
        return ((q[0] + q[1]) / 2.0, (q[0] - q[1]) / 2.0)

    def grow(r, e):
        return (r[0] - e, r[1] + e, r[2] - e, r[3] + e)

    def meet(a, b):
        r = (max(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), min(a[3], b[3]))
        return r if r[0] <= r[1] + 1e-6 and r[2] <= r[3] + 1e-6 else None

    def dist(a, b):
        return max(0.0, a[0] - b[1], b[0] - a[1], a[2] - b[3], b[2] - a[3])

    def near(r, q):            # point of rect r (uv) nearest uv point q (Chebyshev)
        return (min(max(q[0], r[0]), r[1]), min(max(q[1], r[2]), r[3]))
    # drop corner nodes: child re-parented to the corner's parent
    for i in [i for i, n in nodes.items() if n.get("corner")]:
        n = nodes[i]
        par = nodes[n["parent"]]
        par["kids"] = [k for k in par["kids"] if k != i] + n["kids"]
        for k in n["kids"]:
            nodes[k]["parent"] = n["parent"]
        del nodes[i]
    for n in nodes.values():
        n["ideal_xy"] = [n["x"], n["y"]]
    ms, t, edge = {}, {}, {}
    elong = []

    def up(i):
        n = nodes[i]
        if not n["kids"]:
            (part, port, x, y), = n["taps"]           # full-depth FB1: exactly one entry per leaf
            ms[i], t[i] = (uv((x, y))[0],) * 2 + (uv((x, y))[1],) * 2, 0.0
            return
        for k in n["kids"]:
            up(k)
        ks = n["kids"]
        if len(ks) == 1:                                # stage node: transparent (placed on its parent->child path)
            ms[i], t[i] = ms[ks[0]], t[ks[0]]
            return
        a, b = ks[0], ks[1]
        if len(ks) > 2:
            raise ValueError("dme: >2 kids")
        d = dist(ms[a], ms[b])
        x = (d + t[b] - t[a]) / 2.0
        if x < 0 or x > d:                              # needs elongation (reported; not modelled as meander)
            elong.append((i, round(abs(t[a] - t[b]) - d, 3)))
            x = min(max(x, 0.0), d)
        edge[a], edge[b] = x, d - x
        r = meet(grow(ms[a], x), grow(ms[b], d - x))
        if r is None:
            raise ValueError(f"dme: empty merge at node {i}")
        ms[i], t[i] = r, max(t[a] + x, t[b] + d - x)
    root = [i for i, n in nodes.items() if n["parent"] is None][0]
    up(root)
    off = []

    def pick(r, ideal):
        """legal point on the uv rect r nearest the ideal xy (r is a segment or point in practice)."""
        q0 = uv(ideal)
        c = near(r, q0)
        if site.legal(xy(c)):
            return xy(c), 0.0
        du, dv = r[1] - r[0], r[3] - r[2]
        L = max(du, dv)
        n = max(1, int(L / step))
        best = None
        for k in range(n + 1):
            f = k / n
            q = (r[0] + du * f, r[2] + dv * f) if du >= dv or dv < 1e-6 else (r[0] + du * f, r[2] + dv * f)
            p = xy(q)
            if site.legal(p):
                dd = max(abs(q[0] - q0[0]), abs(q[1] - q0[1]))
                if best is None or dd < best[0]:
                    best = (dd, p)
        if best:
            return best[1], 0.0
        p = site.nearest(xy(c))
        return p, max(abs(uv(p)[0] - c[0]), abs(uv(p)[1] - c[1]))

    def down(i, P):
        n = nodes[i]
        if P is not None and len(n["kids"]) == 1:      # stage chain i..k: place k, then the chain on the P->k L path
            chain = [i]
            while len(nodes[chain[-1]]["kids"]) == 1:
                chain.append(nodes[chain[-1]]["kids"][0])
            k = chain.pop()
            edge[k] = edge[i]
            down(k, P)
            px, py = xy((uv_of[P][0], uv_of[P][2]))
            kx, ky = nodes[k]["x"], nodes[k]["y"]
            L = abs(kx - px) + abs(ky - py)
            for j, c in enumerate(chain):             # even stages along P -> (kx, py) -> k (monotone: length kept)
                s_ = L * (j + 1) / (len(chain) + 1)
                hx = abs(kx - px)
                q = (px + (kx - px) * min(s_, hx) / hx if hx > 1e-9 else px,
                     py if s_ <= hx else py + (ky - py) * (s_ - hx) / max(1e-9, L - hx))
                if not site.legal(q):
                    q2 = site.nearest(q, "x" if s_ <= hx else "y")
                    off.append((c, round(abs(q2[0] - q[0]) + abs(q2[1] - q[1]), 3)))
                    q = q2
                nodes[c]["x"], nodes[c]["y"] = round(q[0], 3), round(q[1], 3)
                uv_of[c] = (uv(q)[0], uv(q)[0], uv(q)[1], uv(q)[1])
            return
        if P is None:
            p, o = pick(ms[i], n["ideal_xy"])
        else:
            r = meet(ms[i], grow(uv_of[P], edge[i]))
            if r is None:
                r = ms[i]
            if not n["kids"]:                             # leaf = entry point itself (entries sit in channels)
                p, o = xy(near(r, uv_of[P])), 0.0
                if not site.legal(p):
                    p, o = pick(r, n["ideal_xy"])
            else:
                p, o = pick(r, n["ideal_xy"])
        if o > 1e-3:
            off.append((i, round(o, 3)))
        n["x"], n["y"] = round(p[0], 3), round(p[1], 3)
        uv_of[i] = (uv(p)[0], uv(p)[0], uv(p)[1], uv(p)[1])
        for k in n["kids"]:
            down(k, i)
    uv_of = {}
    down(root, None)
    def lev(i, L):
        nodes[i]["level"] = L
        for k in nodes[i]["kids"]:
            lev(k, L + 1)
    lev(root, 0)
    return dict(mode="dme", root=root, t_root_um=round(t[root], 3), elongations=len(elong),
                elongation_um=round(sum(e for _, e in elong), 3), offsets=len(off), offset_um_max=max([o for _, o in off] or [0.0]),
                offset_um_sum=round(sum(o for _, o in off), 3), first_offsets=off[:12], first_elongations=elong[:12])
