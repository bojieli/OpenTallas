#!/usr/bin/env python3
"""DIE-KV-58/clk (+DIE-KV-61/grt: bare st:<path> occurrences remapped too): remap a count-align bind's START-tree stage paths from an old die_trial tree to a new one.
Rule (diagnostic remap, K/PAD/DEPTH unchanged, same as DIE-KV-47-SD path_remap.json): a stage path names a physical
clock cell (trial_tap_arrivals physical encoding, incl. partial-prefix aliases of the parent output).  The new path is
the new tree's path of the cell at the SAME site (xy) that lies on the same tap's root->driver path; fallback = the
cell on that tap path with the same stage count from the root.
  bind_remap.py OLD_TREE NEW_TREE BIND OUT_BIND OUT_MAP
"""
import json, re, sys
CH = "0123456789abcdefghijklmnopqrstuvwxyz"


def paths(T):
    po = T["parent_of"]; buf = {int(k): v for k, v in T["node_buf"].items()}
    nodes = {int(k): v for k, v in T["nodes"].items()}
    root = next(i for i, n in nodes.items() if n["parent"] is None)
    ch = {}
    for c, p in po.items():
        ch.setdefault(p, []).append(c)
    p2c, c2p = {}, {}
    st = [(buf[root], "h")]
    while st:
        cell, p = st.pop()
        c2p[cell] = p; p2c[p] = cell
        kids = sorted(ch.get(cell, []))
        w = 1
        while 36 ** w < len(kids):
            w += 1
        for k, child in enumerate(kids):
            code = ""; kk = k
            for _ in range(w):
                code = CH[kk % 36] + code; kk //= 36
            for n in range(1, w):
                p2c.setdefault(p + code[:n], cell)
            st.append((child, p + code))
    return p2c, c2p


def chain(T, cell):
    po = T["parent_of"]; out = [cell]
    while cell in po:
        cell = po[cell]; out.append(cell)
    return out[::-1]


def main():
    O, N = (json.load(open(f)) for f in sys.argv[1:3])
    B = open(sys.argv[3]).read()
    op2c, _ = paths(O); np2c, nc2p = paths(N)
    otap = {t["port"]: t for t in O["taps"]}; ntap = {t["port"]: t for t in N["taps"]}
    obuf = {int(k): v for k, v in O["node_buf"].items()}; nbuf = {int(k): v for k, v in N["node_buf"].items()}
    toks = set(re.findall(r"(?:st:|__st__)(h[0-9a-z]*)@", B)) | set(re.findall(r'"fork_node": "(h[0-9a-z]*)"', B))
    # tap context of each token: the '@t_...__clk' tap at the end of the key chain it appears in
    ctx = {}
    for m in re.finditer(r"(?:st:|__st__)(h[0-9a-z]*)@((?:st:h[0-9a-z]*@)*)(t_[A-Za-z0-9_]+__clk[A-Za-z0-9_]*)", B):
        ctx.setdefault(m.group(1), m.group(3))
    for m in re.finditer(r'"fork_node": "(h[0-9a-z]*)"', B):
        pass
    mp, how = {}, {"xy": 0, "stage": 0, "fail": 0, "same": 0}
    for p in sorted(toks):
        if p not in op2c:
            how["fail"] += 1; continue
        cell = op2c[p]; xy = O["sites"][cell]; tap = ctx.get(p)
        cand = None
        if p in np2c and N["sites"][np2c[p]] == xy:
            mp[p] = p; how["same"] += 1; how["xy"] += 1
            continue
        if tap and tap in ntap:
            nt = ntap[tap]; nd = nt.get("driver", nbuf[nt["node"]]); nch = chain(N, nd)
            hit = [c for c in nch if N["sites"][c] == xy]
            if hit:
                cand = hit[0]; how["xy"] += 1
            else:
                ot = otap[tap]; od = ot.get("driver", obuf[ot["node"]]); och = chain(O, od)
                if cell in och and och.index(cell) < len(nch):
                    cand = nch[och.index(cell)]; how["stage"] += 1
        else:
            hit = [c for c, s in N["sites"].items() if s == xy]
            if len(hit) == 1:
                cand = hit[0]; how["xy"] += 1
        if cand is None and p in np2c and abs(N["sites"][np2c[p]][0] - xy[0]) + abs(N["sites"][np2c[p]][1] - xy[1]) <= 50:
            cand = np2c[p]; how["near_same_path"] = how.get("near_same_path", 0) + 1   # legalization nudge only
        if cand is None:
            best = min(N["sites"], key=lambda c: abs(N["sites"][c][0] - xy[0]) + abs(N["sites"][c][1] - xy[1]))
            if abs(N["sites"][best][0] - xy[0]) + abs(N["sites"][best][1] - xy[1]) <= 50:
                cand = best; how["nearest"] = how.get("nearest", 0) + 1
        if cand is None:
            how["fail"] += 1; continue
        mp[p] = nc2p[cand]
        how["same"] += mp[p] == p
    def sub(m):
        return m.group(1) + mp.get(m.group(2), m.group(2)) + m.group(3)
    B2 = re.sub(r"(st:|__st__)(h[0-9a-z]*)(@|(?![0-9a-z]))", sub, B)   # DIE-KV-61/grt: also bare st:<path> keys / parent chains
    B2 = re.sub(r'("fork_node": ")(h[0-9a-z]*)(")', sub, B2)
    open(sys.argv[4], "w").write(B2)
    json.dump(dict(rule=__doc__.splitlines()[1], counts=how, tokens=len(toks), map=mp), open(sys.argv[5], "w"), indent=1)
    print(json.dumps(dict(tokens=len(toks), **how)))
    return 0 if how["fail"] == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
