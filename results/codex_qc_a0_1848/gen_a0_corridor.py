"""DIE-QC-39 A0: gen_a0_tree21.py (DIE-QC-37) + OPT-IN standard stages. Without the new flags the slice, report and
stdout are byte-identical to gen_a0_tree21.py (test_gen_a0_tree39.py).
  --std-leg L      every spread node is placed exactly L um (Manhattan) from its parent: when the even pace
                   (centroid - parent) / remaining levels is shorter than L the node also steps sideways (zig-zag), so
                   short filler legs (DIE-QC-38: 14 ps FF) become standard legs; the reach / split / corridor arithmetic
                   uses the window top --std-max (default 60): macro chains r = ceil(corridor / max), domain gate depth by
                   far / max.  A macro gate keeps depth >= ceil(|port - gate| / max) + 1; if T - k - r is shallower,
                   r shrinks (longer chain legs, reported).  Legs that the geometry forces over the window are reported.
  --std-split f    std mode: a node splits when its load spread > reach * (levels left - 1) * f (default 1 = T21 rule)
  --std-fan n      std mode: max fanout of every planned node (default 4 = T21; 2 = fixed fanout-2 stages)
  --leaf-max N     register leaf size (equal counts, default 21 as T21).
  --stage-ff/--stage-tt  measured standard stage for the early-tap k (core_tree.early_tap_stage_ps), with --stage-src.
DIE-QC-37 docstring follows.

DIE-QC-37 A0: deeper planned tile clock tree (COORD 14:18 item 4, "T21") for qfd_tile_nl_a0c / qfd_tile_nk_a0c.

Successor of results/qc_die36_1029/a0/gen_a0_tree.py (T11, single t7 fan-out -> FAIL) and the Codex T15 --spread WIP
(codex/qc-a0-1355). Plan/census data only (no timing measurement):
  * every macro hop ICG keeps its GEOM-PASS placed xy; register-free clock repeaters follow the gate along the straight
    gate -> macro clock PIN line (pin from the macro LEF + placement orient), each node legalised outside the macro
    halos; legs <= --leg um; the last repeater (the macro leaf) sits at the legal point nearest the pin; macro view
    insertion k (signed Liberty min/max_clock_tree_path / plan stage model) closes the total: gate depth = T - k - r.
  * root registers: equal-count leaves (ceil(N/21) groups) at depth T.
  * register hop ICGs: (open)    CTS-open leaf below the gate, cts_stages 3, gate depth T-3 (V1);
                       (planned) planned domain: the gate keeps its xy, its domain is split into equal-count register
                                 leaves (same window as the root leaves) built through the same bounded spread (V2).
  * one bounded spread from the port node R: fanout <= 4 per node; a node splits only when a load must attach, the
    fan-out depth demands it, or the load spread exceeds what one more leg can reach; otherwise it walks one leg
    toward the load centroid (nodes at parent + (centroid - parent) / remaining levels).
Equal TOTAL stage count T on every leaf (core_infra stage_basis total); no pads, trims or delay cells.
    python3 -I gen_a0_tree21.py --kit KIT --census n?.tsv.gz --out slice.json --report rep.json --stages 21 \
        --leg 150 --reg-domains open|planned [--png plan.png]
"""
import argparse, gzip, hashlib, json, math, re
from pathlib import Path

STAGE = {"TT": 36.154, "FF": 27.549,
         "source": "tools/die_plan/clk_aocv_table_g021.json clock_aocv.classes.B.{TT,FF}.mu_stage_ps (core tree stage)"}
LEAF_MAX = 21          # register leaf size window [20, 21] for every domain of 420+ sinks (ceil(N/21) leaves)
FAN = 4
CTS_STAGES = 3
NODE, LEAF, MLEAF = "BUFx12f_ASAP7_75t_R", "BUFx8_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R"
HALO = (5.8, 4.6)
BOX = (6.0, 4.8, 451.9, 1152.9)


def lib_insertion(path):
    txt = Path(path).read_text()
    out = {}
    for kind in ("min", "max"):
        m = re.search(kind + r"_clock_tree_path;\s*cell_rise\(scalar\)\s*\{\s*values\(\"([0-9.]+)\"\);\s*\}\s*"
                      r"cell_fall\(scalar\)\s*\{\s*values\(\"([0-9.]+)\"\);", txt)
        if not m:
            raise SystemExit(f"{path}: no {kind}_clock_tree_path")
        a, b = float(m[1]), float(m[2])
        out[kind] = min(a, b) if kind == "min" else max(a, b)
    return out


def lef_geom(path, pin="clk"):
    txt = Path(path).read_text()
    w, h = map(float, re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", txt).groups())
    m = re.search(r"PIN " + pin + r"\b.*?RECT\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", txt, re.S)
    x0, y0, x1, y1 = map(float, m.groups())
    return w, h, ((x0 + x1) / 2, (y0 + y1) / 2)


def place_pin(at, orient, w, h, p):
    px, py = p
    if orient == "R0":
        return [at[0] + px, at[1] + py]
    if orient == "MY":
        return [at[0] + w - px, at[1] + py]
    if orient == "MX":
        return [at[0] + px, at[1] + h - py]
    if orient == "R180":
        return [at[0] + w - px, at[1] + h - py]
    raise SystemExit(f"orient {orient} unsupported")


def split(pts, counts):
    if len(counts) == 1:
        return [pts]
    h = len(counts) // 2
    n1 = sum(counts[:h])
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    axis = 0 if max(xs) - min(xs) >= max(ys) - min(ys) else 1
    pts = sorted(pts, key=lambda p: (p[axis], p[1 - axis]))
    return split(pts[:n1], counts[:h]) + split(pts[n1:], counts[h:])


def equal_counts(n, k):
    return [n // k + (1 if i < n % k else 0) for i in range(k)]


def centroid(pts):
    return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Planner:
    def __init__(self, boxes, leg, std_leg=None):
        self.boxes, self.leg, self.nodes, self.serial = boxes, leg, [], 0
        self.std_leg = std_leg
        self.corridor_feed = False
        self.fan = FAN               # --std-fan (std mode only): max fanout of every planned node
        self.split_f = 1.0           # --std-split (std mode only): split when spread > reach * (rem - 1) * f

    def std_pos(self, pxy, gc, r):
        """--std-leg: child of pxy toward centroid gc with r levels left to the nearest load: a leg of exactly std_leg
        whose end leaves |X - gc| = std_leg when one leg remains, else the even-pace remainder; when the even pace
        is already >= std_leg the even-pace point (DIE-QC-37 rule) is kept."""
        L = self.std_leg
        even = [pxy[0] + (gc[0] - pxy[0]) / r, pxy[1] + (gc[1] - pxy[1]) / r]
        dist = man(pxy, gc)
        if dist / r >= L:
            return even
        rem = L if r - 1 == 1 else dist * (r - 1) / r
        best = None
        for i in range(144):
            u = 4.0 * i / 144                                  # walk the L-diamond perimeter
            q, f = int(u), u - int(u)
            dx, dy = ((1 - f, f), (-f, 1 - f), (f - 1, -f), (f, f - 1))[q]
            x, y = pxy[0] + L * dx, pxy[1] + L * dy
            if not (BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3]) or self.blocked(x, y):
                continue
            key = (round(abs(man((x, y), gc) - rem), 3), round(man((x, y), even), 3))
            if best is None or key < best[0]:
                best = (key, [x, y])
        return best[1] if best else even

    def legal(self, pt):
        x = max(BOX[0], min(BOX[2], pt[0])); y = max(BOX[1], min(BOX[3], pt[1]))
        pending, seen, ok = [(x, y)], set(), []
        while pending:
            x, y = pending.pop(); key = (round(x, 3), round(y, 3))
            if key in seen:
                continue
            seen.add(key)
            hit = next((b for b in self.boxes if b[0] < x < b[2] and b[1] < y < b[3]), None)
            if hit:
                for q in ((hit[0], y), (hit[2], y), (x, hit[1]), (x, hit[3])):
                    if BOX[0] <= q[0] <= BOX[2] and BOX[1] <= q[1] <= BOX[3]:
                        pending.append(q)
            else:
                ok.append((x, y))
        if not ok:
            raise ValueError("no legal planned buffer site")
        return [round(v, 3) for v in min(ok, key=lambda q: man(q, pt))]

    def blocked(self, x, y):
        return any(b[0] < x < b[2] and b[1] < y < b[3] for b in self.boxes)

    def corridor(self, a, b, step=3.0):
        """Shortest Manhattan path a -> b on a step-um grid avoiding every macro halo box (legal corridors only)."""
        import heapq
        q = lambda p: (round(p[0] / step), round(p[1] / step))
        sa, sb = q(a), q(b)
        nx, ny = int(BOX[2] / step) + 2, int(BOX[3] / step) + 2
        dist, prev, pq = {sa: 0}, {}, [(0, sa)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == sb:
                break
            if d > dist[u]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                v = (u[0] + dx, u[1] + dy)
                if not (0 <= v[0] <= nx and 0 <= v[1] <= ny) or (v != sb and self.blocked(v[0] * step, v[1] * step)):
                    continue
                # small bend penalty keeps the path an L / Z, not a staircase
                bend = 0.01 if u in prev and (u[0] - prev[u][0], u[1] - prev[u][1]) != (dx, dy) else 0
                nd = d + step + bend
                if nd < dist.get(v, 1e18):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
        if sb not in dist:
            raise ValueError("no macro-free corridor")
        pts, u = [], sb
        while u != sa:
            pts.append([u[0] * step, u[1] * step]); u = prev[u]
        pts = [list(a)] + pts[::-1][:-1] + [list(b)]
        out = [pts[0]]                       # keep corners only
        for i in range(1, len(pts) - 1):
            if (pts[i][0] - out[-1][0]) * (pts[i + 1][1] - pts[i][1]) != (pts[i][1] - out[-1][1]) * (pts[i + 1][0] - pts[i][0]):
                out.append(pts[i])
        return out + [pts[-1]]

    @staticmethod
    def along(path, s):
        for i in range(len(path) - 1):
            l = man(path[i], path[i + 1])
            if s <= l or i == len(path) - 2:
                f = min(1.0, s / l) if l else 0.0
                return [path[i][0] + (path[i + 1][0] - path[i][0]) * f, path[i][1] + (path[i + 1][1] - path[i][1]) * f]
            s -= l

    def node(self, prefix, xy, parent, master=NODE):
        self.serial += 1
        n = dict(name=f"mp_a0_{prefix}{self.serial}", master=master, xy_um=self.legal(xy), parent=parent)
        self.nodes.append(n)
        return n

    def feed(self, parent, pxy, d, items, prefix):
        """parent (at depth d, xy pxy) drives items (dict xy, goal >= d+1, attach(parent_name))."""
        ready = [q for q in items if q["goal"] == d + 1]
        later = [q for q in items if q["goal"] > d + 1]
        if any(q["goal"] <= d for q in items):
            raise ValueError(f"depth {d}: load deeper than its goal")
        if len(ready) > self.fan or (len(ready) == self.fan and later):
            raise Collision(d, ready)
        for q in ready:
            q["attach"](parent)
        if not later:
            return
        rem = min(q["goal"] for q in later) - d          # levels left for the nearest-goal later load
        cap = self.fan - len(ready)
        c = centroid([q["xy"] for q in later])
        spread = max(man(q["xy"], c) for q in later)
        # fan-out feasibility: a single child at d+1 can reach at most FAN**(rem-1) loads at the nearest goal
        need_split = (len(later) > self.fan ** max(0, rem - 1)) or spread > self.leg * max(1, rem - 1) * self.split_f or rem <= 1
        nb = min(cap, len(later)) if need_split else 1
        for grp in split([(*q["xy"], q) for q in later], equal_counts(len(later), nb)):
            kids = [g[2] for g in grp]
            gc = centroid([q["xy"] for q in kids])
            r = min(q["goal"] for q in kids) - d
            if self.corridor_feed:
                path = self.corridor(pxy, self.legal(gc), step=6.0)
                plen = sum(man(path[i], path[i+1]) for i in range(len(path)-1))
                pos = self.along(path, max(plen / r, min(self.std_leg or 0, plen)))
            elif self.std_leg:
                pos = self.std_pos(pxy, gc, r)
            else:
                pos = [pxy[0] + (gc[0] - pxy[0]) / r, pxy[1] + (gc[1] - pxy[1]) / r]
            nd = self.node(prefix, pos, parent)
            self.feed(nd["name"], nd["xy_um"], d + 1, kids, prefix)


class Collision(Exception):
    def __init__(self, d, ready):
        super().__init__(f"depth {d}: {len(ready)} fixed-depth loads")
        self.d, self.ready = d, ready


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", required=True); ap.add_argument("--census", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--report"); ap.add_argument("--png")
    ap.add_argument("--stages", type=int, default=21); ap.add_argument("--leg", type=float, default=150.0)
    ap.add_argument("--reg-domains", choices=("open", "planned"), default="open")
    ap.add_argument("--dpl-max", type=float, default=60.0)
    ap.add_argument("--corridor-feed", action="store_true")
    ap.add_argument("--std-leg", type=float, default=None)
    ap.add_argument("--std-max", type=float, default=60.0)
    ap.add_argument("--std-split", type=float, default=1.0)
    ap.add_argument("--std-fan", type=int, default=FAN)
    ap.add_argument("--leaf-max", type=int, default=LEAF_MAX)
    ap.add_argument("--stage-ff", type=float, default=None); ap.add_argument("--stage-tt", type=float, default=None)
    ap.add_argument("--stage-src", default=None)
    a = ap.parse_args()
    T = a.stages
    std = a.std_leg is not None
    reach = a.std_max if std else a.leg          # reach / split / corridor leg
    stage = STAGE
    if (a.stage_ff is None) != (a.stage_tt is None) or (a.stage_ff is not None and not a.stage_src):
        raise SystemExit("--stage-ff, --stage-tt and --stage-src go together")
    if a.stage_ff is not None:
        stage = {"TT": a.stage_tt, "FF": a.stage_ff, "source": a.stage_src}
    kd = Path(a.kit)
    sl = json.loads((kd / "master_slice.json").read_text())
    fr = json.loads((kd / "freeze.json").read_text())
    port, root, dom, gates = None, [], {}, {}
    for line in gzip.open(a.census, "rt"):
        f = line.rstrip("\n").split("\t")
        if line.startswith("port "):
            _, _, x, y = line.split(); port = [float(x), float(y)]
            continue
        if f[0] != "S":
            continue
        path, depth, inst, pin, master, x, y = f[1], int(f[2]), f[3], f[4], f[5], float(f[6]), float(f[7])
        if depth == 0:
            if master.startswith("ICG"):
                gates[inst] = dict(master=master, xy=[x, y])
            else:
                root.append((x, y, f"{inst}/{pin}"))
        elif depth == 1:
            dom.setdefault(path.split(">", 1)[1], []).append(dict(inst=inst, pin=pin, master=master, xy=[x, y]))
    assert set(gates) == set(dom), set(gates) ^ set(dom)
    hard = {h["inst"]: h for h in fr["hard_children"]}
    boxes, geo = [], {}
    for h in fr["hard_children"]:
        if h["master"] not in geo:
            geo[h["master"]] = lef_geom(kd / "macros" / f"{h['master']}.lef")
        w, hh, _ = geo[h["master"]]
        x, y = h["at"]
        boxes.append((x - HALO[0], y - HALO[1], x + w + HALO[0], y + hh + HALO[1]))
    views = {}
    mac_gates, reg_gates = [], []
    for g in sorted(dom):
        s = dom[g]
        if len(s) == 1 and s[0]["master"].startswith("ot_qwen_tile_"):
            m = s[0]["master"]
            if m not in views:
                ff, tt = kd / "macros" / f"{m}_ff.lib", kd / "macros" / f"{m}_tt.lib"
                views[m] = dict(FF=lib_insertion(ff), TT=lib_insertion(tt),
                                view=f"macros/{m}_{{tt,ff}}.lib sha256 tt:{hashlib.sha256(tt.read_bytes()).hexdigest()[:16]} "
                                     f"ff:{hashlib.sha256(ff.read_bytes()).hexdigest()[:16]} (min/max_clock_tree_path)")
            mac_gates.append(g)
        else:
            reg_gates.append(g)
    P = Planner(boxes, reach, a.std_leg)
    P.corridor_feed = a.corridor_feed
    if std:
        P.split_f, P.fan = a.std_split, a.std_fan
    elif a.std_split != 1.0 or a.std_fan != FAN:
        raise SystemExit("--std-split / --std-fan need --std-leg")
    glist, leaves, items, early, mac_chain = [], [], [], [], {}
    # ---- macro branches: gate (fixed xy) -> r repeaters along the gate -> pin line -> macro clk pin (k view stages)
    for g in mac_gates:
        s = dom[g][0]
        inst = s["inst"].replace("\\", "")
        h = hard[inst]
        w, hh, p = geo[h["master"]]
        pin = place_pin(h["at"], h["orient"], w, hh, p)
        v = views[s["master"]]
        ins = {c: {"min": v[c]["min"], "max": v[c]["max"]} for c in ("TT", "FF")}
        k = int(math.floor(((ins["FF"]["min"] + ins["FF"]["max"]) / 2) / stage["FF"] + 0.5))
        gxy = gates[g]["xy"]
        cpath = P.corridor(gxy, P.legal(pin))
        clen = sum(man(cpath[i], cpath[i + 1]) for i in range(len(cpath) - 1)) + man(P.legal(pin), pin)
        r = max(1, math.ceil(clen / reach))
        if std:     # keep the gate reachable by standard legs from the port: shrink r (longer chain legs) if needed
            gmin = max(2, math.ceil(man(port, gxy) / reach) + 1)
            if T - k - r < gmin:
                r = T - k - gmin
                if r < 1:
                    raise SystemExit(f"{g}: T {T} too shallow for k {k} + gate depth {gmin}")
        mac_chain[g] = dict(pin=pin, k=k, r=r, corridor_um=round(clen, 1), ins=ins, view=v["view"], sink=f"{s['inst']}/{s['pin']}", macro=s["master"])
    if a.reg_domains == "planned":
        dom_leaves = {}
        for g in reg_gates:
            pts = [(*q["xy"], f"{q['inst']}/{q['pin']}") for q in dom[g]]
            dom_leaves[g] = split(pts, equal_counts(len(pts), math.ceil(len(pts) / a.leaf_max)))
    root_groups = split(root, equal_counts(len(root), math.ceil(len(root) / a.leaf_max)))
    gate_goal = {}
    for g in mac_gates:
        gate_goal[g] = T - mac_chain[g]["k"] - mac_chain[g]["r"]
    for g in reg_gates:
        if a.reg_domains == "open":
            gate_goal[g] = T - CTS_STAGES
        else:
            lv = dom_leaves[g]
            far = max(man(gates[g]["xy"], centroid(grp)) for grp in lv)
            if a.corridor_feed:
                lengths = []
                for grp in lv:
                    walk = P.corridor(gates[g]["xy"], P.legal(centroid(grp)), step=6.0)
                    lengths.append(sum(man(walk[j], walk[j+1]) for j in range(len(walk)-1)))
                far = max(lengths)
            gate_goal[g] = T - max(math.ceil(math.log(len(lv), P.fan)) + 1, math.ceil(far / reach) + 1)
    for attempt in range(40):
        P.nodes, P.serial = [], 0
        glist, leaves, early = [], [], []
        R = P.node("R", [port[0], port[1] + 2.0], "port:ck", master="BUFx24_ASAP7_75t_R")
        items = []
        recs = {}
        for g in mac_gates + reg_gates:
            rec = dict(inst=g, master=gates[g]["master"], parent=None, xy_um=gates[g]["xy"])
            if g in mac_gates or a.reg_domains == "planned":
                rec["domain"] = "planned"
            recs[g] = rec
            items.append(dict(xy=gates[g]["xy"], goal=gate_goal[g], attach=lambda par, rec=rec: rec.__setitem__("parent", par)))
        root_leaf_recs = []
        for i, grp in enumerate(root_groups):
            rec = dict(name=f"mp_a0_lr{i}", master=LEAF, xy_um=P.legal(centroid(grp)), parent=None)
            root_leaf_recs.append(rec)
            items.append(dict(xy=rec["xy_um"], goal=T, attach=lambda par, rec=rec: rec.__setitem__("parent", par)))
            leaves.append(dict(node=rec["name"], sinks=[q[2] for q in grp]))
        try:
            P.feed(R["name"], R["xy_um"], 1, items, "s")
        except Collision as e:
            # shift one colliding gate one stage up (one more repeater after it / one more domain level below it)
            gs = sorted((g for g in gate_goal if gate_goal[g] == e.d + 1), key=lambda g: man(gates[g]["xy"], port))
            if not gs:
                raise
            g = gs[-1]
            gate_goal[g] -= 1
            if g in mac_chain:
                mac_chain[g]["r"] += 1
            continue
        break
    else:
        raise SystemExit("could not resolve fixed-depth collisions")
    upper = list(P.nodes)
    P.nodes = []
    nodes_under = []
    for g in mac_gates + reg_gates:
        glist.append(recs[g])
    for g in mac_gates:
        mc = mac_chain[g]
        gxy, pin, r = gates[g]["xy"], mc["pin"], mc["r"]
        par = g
        path = P.corridor(gxy, P.legal(pin))
        plen = sum(man(path[i], path[i + 1]) for i in range(len(path) - 1))
        for i in range(1, r + 1):
            pos = pin if i == r else P.along(path, plen * i / r)
            nd = P.node("m", pos, par, master=MLEAF if i == r else NODE)
            par = nd["name"]
        leaves.append(dict(node=par, sinks=[mc["sink"]], load_class="macro", early_tap_ps=mc["ins"],
                           early_tap_view=mc["view"]))
        early.append(dict(gate=g, macro=mc["macro"], k=mc["k"], r=r, gate_depth=gate_goal[g], leaf_depth=T - mc["k"],
                          gate_pin_um=round(man(gxy, pin), 1), corridor_um=mc["corridor_um"]))
    if a.reg_domains == "open":
        for g in reg_gates:
            leaves.append(dict(node=g, load_class="gated_domain", domain_sinks=len(dom[g]), cts_stages=CTS_STAGES))
    else:
        for g in reg_gates:
            its = []
            for i, grp in enumerate(dom_leaves[g]):
                rec = dict(name=f"mp_a0_ld{g.split('.')[-1].split('/')[0].replace('u_hop_', '')}_{i}", master=LEAF,
                           xy_um=P.legal(centroid(grp)), parent=None)
                its.append(dict(xy=rec["xy_um"], goal=T, rec=rec,
                                attach=lambda par, rec=rec: rec.__setitem__("parent", par)))
                leaves.append(dict(node=rec["name"], sinks=[q[2] for q in grp]))
            P.feed(g, gates[g]["xy"], gate_goal[g], its, "d")
            for q in its:
                P.nodes.append(q["rec"])
    nodes = upper + root_leaf_recs + P.nodes
    # ---- order: nodes above gates, then (deferred) nodes below gates in parent-first order
    below_ids = {id(m) for m in P.nodes}
    above = [n for n in nodes if n["parent"] == "port:ck" or id(n) not in below_ids]
    below = [n for n in nodes if id(n) in below_ids]
    known = {"port:ck"} | {n["name"] for n in above}
    order = []
    pend = list(above)
    while pend:
        nx = [n for n in pend if n["parent"] in known or n["parent"] == "port:ck"]
        if not nx:
            raise SystemExit("cycle above gates")
        for n in nx:
            order.append(n); known.add(n["name"])
        pend = [n for n in pend if n not in nx]
    known |= set(gates)
    pend = list(below)
    while pend:
        nx = [n for n in pend if n["parent"] in known]
        if not nx:
            raise SystemExit("cycle below gates")
        for n in nx:
            order.append(n); known.add(n["name"])
        pend = [n for n in pend if n not in nx]
    nodes = order
    # ---- geometry census (every leg incl. leaf -> sink)
    xy = {"port:ck": port, **{n["name"]: n["xy_um"] for n in nodes}, **{g["inst"]: g["xy_um"] for g in glist}}
    depth = {"port:ck": 0}
    par = {n["name"]: n["parent"] for n in nodes}
    par.update({g["inst"]: g["parent"] for g in glist})
    def dep(n):
        if n not in depth:
            depth[n] = dep(par[n]) + 1
        return depth[n]
    fan, arcs = {}, []
    for n, p in par.items():
        fan[p] = fan.get(p, 0) + 1
        arcs.append((man(xy[p], xy[n]), p, n))
    sink_xy = {f"{q['inst']}/{q['pin']}": q["xy"] for g in dom for q in dom[g]}
    sink_xy.update({r_[2]: [r_[0], r_[1]] for r_ in root})
    leaf_legs = []
    for lf in leaves:
        for s in lf.get("sinks", []):
            sxy = mac_chain[next(g for g in mac_gates if mac_chain[g]["sink"] == s)]["pin"] if lf.get("load_class") == "macro" else sink_xy[s]
            leaf_legs.append((man(xy[lf["node"]], sxy), lf["node"], s, lf.get("load_class", "register")))
    tot = {}
    for lf in leaves:
        extra = lf.get("cts_stages", 0) + (next((e["k"] for e in early if lf.get("load_class") == "macro" and
                                                  mac_chain[e["gate"]]["sink"] == lf["sinks"][0]), 0))
        tot[dep(lf["node"]) + extra] = tot.get(dep(lf["node"]) + extra, 0) + 1
    def cls(n):
        return "gate" if n in gates else n.split("_")[2].rstrip("0123456789") if n.startswith("mp_a0_") else n
    node_legs = sorted(arcs, reverse=True)
    geom = dict(max_fanout=max(fan.values()), max_node_leg_um=round(node_legs[0][0], 1),
                node_legs_over=[(round(l, 1), p, n) for l, p, n in node_legs if l > a.leg][:20],
                max_leaf_sink_leg_um={c: round(max([l for l, _, _, cc in leaf_legs if cc == c] or [0]), 1)
                                      for c in ("register", "macro")},
                total_stage_counts=tot, cells=len(nodes))
    sl["core_tree"] = dict(clock_port=sl.get("core_clock_port", "ck"), stage_basis="total", install_stage="pre_cts",
                           late_dpl_max_um=a.dpl_max, early_tap_stage_ps=stage, nodes=nodes, gates=glist,
                           leaves=leaves,
                           note=(f"DIE-QC-37 A0 T{T} plan tree (gen_a0_tree21.py leg {a.leg} um, reg domains "
                                 f"{a.reg_domains}): census of the GEOM PASS-COND 3_place, macro early taps from the "
                                 "macro Liberty views; no timing measurement") if not std else
                                (f"DIE-QC-39 A0 T{T} standard-stage plan tree (gen_a0_tree39.py std leg {a.std_leg} um, "
                                 f"window max {a.std_max} um, leaf {a.leaf_max}, reg domains {a.reg_domains}): census of the "
                                 "GEOM PASS-COND 3_place, macro early taps from the macro Liberty views; no timing measurement"))
    Path(a.out).write_text(json.dumps(sl, indent=1) + "\n")
    rep = dict(T=T, leg_um=a.leg, reg_domains=a.reg_domains, port=port, reg_gates=len(reg_gates),
               mac_gates=len(mac_gates), root_registers=len(root), root_leaves=len(root_groups),
               gate_depth={g.split(".")[-1].split("/")[0]: gate_goal[g] for g in gate_goal}, early=early, geometry=geom,
               attempts=attempt + 1)
    if std:
        nl_ = [l for l, p_, n_ in arcs if p_ != "port:ck" and n_ not in gates]
        wl = a.std_max
        rep["std_stage"] = dict(std_leg=a.std_leg, window_max=wl, std_split=a.std_split, std_fan=a.std_fan, leaf_max=a.leaf_max, early_tap_stage_ps=stage,
                                node_legs=len(nl_), legs_under_2_3_std=sum(l < a.std_leg * 2 / 3 for l in nl_),
                                legs_over_window=sum(l > wl for l in nl_), legs_over_1p5_window=sum(l > 1.5 * wl for l in nl_),
                                gate_legs_over_window=sorted([(round(l, 1), n_) for l, p_, n_ in arcs if n_ in gates and l > wl], reverse=True)[:40],
                                macro_chain_leg_um={e["gate"].split(".")[-1].split("/")[0]: round(e["corridor_um"] / e["r"], 1) for e in early},
                                leaf_sink_leg_max_um=geom["max_leaf_sink_leg_um"])
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(T=T, cells=len(nodes), geometry={k: v for k, v in geom.items() if k != "node_legs_over"},
                          legs_over=len(geom["node_legs_over"]), attempts=attempt + 1)))
    if std:
        print(json.dumps({k: v for k, v in rep["std_stage"].items() if k != "gate_legs_over_window"}))
    if a.png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 16))
        for b in boxes:
            ax.add_patch(plt.Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc="#ddd", ec="#888", lw=0.5))
        for l, p, n in arcs:
            dd = dep(n)
            col = plt.cm.viridis(dd / T)
            ax.plot([xy[p][0], xy[n][0]], [xy[p][1], xy[n][1]], color=col, lw=0.6 if l <= a.leg else 2.0)
        for l, n, s, c in leaf_legs:
            if c == "macro":
                sxy = mac_chain[next(g for g in mac_gates if mac_chain[g]["sink"] == s)]["pin"]
                ax.plot([xy[n][0], sxy[0]], [xy[n][1], sxy[1]], color="red", lw=1.2)
                ax.plot(*sxy, "r*", ms=8)
        ax.scatter([r_[0] for r_ in root], [r_[1] for r_ in root], s=0.3, c="#c80")
        ax.scatter([g["xy_um"][0] for g in glist], [g["xy_um"][1] for g in glist], s=14, c="blue", marker="s", zorder=5)
        ax.scatter([n["xy_um"][0] for n in nodes], [n["xy_um"][1] for n in nodes], s=2, c="k", zorder=4)
        ax.plot(*port, "g^", ms=10)
        ax.set_xlim(0, 457.92); ax.set_ylim(0, 1157.76); ax.set_aspect("equal")
        ax.set_title(f"{kd.name}\nT{T} leg<={a.leg} reg={a.reg_domains} cells={len(nodes)} maxleg={geom['max_node_leg_um']}",
                     fontsize=8)
        fig.savefig(a.png, dpi=110, bbox_inches="tight")


if __name__ == "__main__":
    main()
