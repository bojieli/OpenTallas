#!/usr/bin/env python3
"""DIE-HBM-61/SPLIT d44v part 6, DIE-HBM-62/BIG part 7: the SPLIT cores become plan designs inside their parent slots (OWNER 18:57: build
the conservative form now).

Per split core (SPEC entry; connectivity = split_conn.py on the thin parent glue <core>__p6glue.sv, which maps every
sub-core port bit to the parent plan pins it reaches and to the peer sub-cores it meets):
  * slot: the parent slot (outline, origin, orient, parent pins / stations / taps around it) is kept.  hard_cores[]
    loses the core entry and gets one entry per sub-core, tiled inside the slot along its long axis.
      - different subs: areas by the sub cell estimates, a street of 4.32-12.96 um between tiles;
      - identical replicas: equal tiles, abutted when the slot divides on the 8.64 lattice;
      - every tile edge lands on the 8.64 lattice in R0 and mirrored instances (track_offset_um 0);
      - the sub order is the permutation with the least pin displacement.
  * names: logical inst <core inst>__<tag> carries bind / clock / pins identity.  physical_inst
    <core inst>.u_fcore.u_core.<u_sub> with physical_master is the bound-netlist path through the glue.
  * pin tables: ONE table per sub module, shared by identical replicas, with orient applied per instance.
      - Bits that reach a parent pin keep its face and position, clamped into the tile.  If the tile does not own
        that face, the nearest outer face of the tile is used.
      - Sub-to-sub seam bits go on the face toward the peer, in the same order on both ends.
      - Clock bits (gen_core_kit_hbm CLK_RE) go to the sub's plan centre clock entry: an M5 interior pin on every
        2nd track, the same placement as clock_entry_pins.
      - Unconnected bits go on the least loaded outer face.
      - N/S faces use M5 and W/E faces use M4, 0.096 um inside the edge, on every 2nd track where it fits.
  * core_faces pass: the check.py core_faces model (as mk_repin) scores each sub port.  A port group whose mean cos
    is < 0 moves to the outer face of its tile that scores best over all instances.
  * sidecars, re-pointed from the core inst to its subs:
      - clock_entries.json: one entry per sub at its tile centre, 4.32 PG lattice, or at the spec point clear of
        the macros.
      - clock.taps: one tap per sub.
      - core_conns.json: the sub's own ports, the parent targets, the seam peers, and the partners' core:<sub>.
      - internal_stations launch/capture/conn: <inst>.<port> goes to the sub that owns the port (the sub port name);
        a bare <inst> goes to the sub tile nearest the station end point.
      - core_macros.json: the sub macro sites (spec 'macros').
      - parent_id_straps: move to the sub that owns those pins.
Part 8 spec options: keep_face = a sub inside the slot keeps a parent pin's face (its wires pass over the tile on that side);
  hub_sub = a net shared by several subs places its seam pin toward this sub.
Part 7 spec options (cores with too many subs for the permutation search, masters shared between slots):
  * layout {sub inst: {xy, wh, orient}}: explicit tiles in the core frame.  orient R0 / MX / MY / R180 mirrors the sub
    inside the slot and composes with the parent orient.  Seam pins go on the N / S face toward the peer, one group per
    peer in natural bit order, so tile-to-tile wires do not cross.
  * a module used by several cores gets ONE pin table: wants of all its instances, in the sub frame.  Outlines must match.
  * boundary_sub: the sub holding the core's outer interface; bus-level station refs and partner conns go to it.
  * the core_faces pass does not move pins of layout cores: the layout already sets the faces.
  * sub_face {sub module: {port base: face}}: the pin face in the SUB frame (replicas mirrored differently want different core faces).
The registered faces are the sub kit face shells: +1 in and +1 out per sub pin.  The cycles they add are the SPLIT EQ
shift maps (SPEC added_cycles; latency tables on claude/die-hbm-61-split-1103).
    python3 mk_split.py PLAN_DIR SPEC.json SPEC_DIR [--only core,...]       (in place; writes split_event.json)"""
import copy, collections, itertools, json, math, re, sys
from pathlib import Path

d = Path(sys.argv[1]); SPEC = json.loads(Path(sys.argv[2]).read_text()); SD = Path(sys.argv[3])
only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import check as CK, schema as SC                                       # noqa: E402
pp = d / "die_plan.json"; P = json.loads(pp.read_text())
G, PG, ST_MIN, EDGE, PITCH, OFF = 8.64, 4.32, 4.32, 0.096, 0.048, 0.024
CLK_RE = r"^(clk|clk_[a-z0-9_]+|[a-z0-9_]*_clk|ck|ck_[a-z0-9_]+|[a-z0-9_]*clk_[a-z0-9_]*)$"
r3 = lambda v: round(v + 0.0, 3)
snap = lambda v, g=G: r3(round(v / g) * g)
trk = lambda v: r3(OFF + round((v - OFF) / PITCH) * PITCH)          # nearest M4/M5 track (0.048 pitch, 0.024 offset)
base = lambda n: re.sub(r"\[\d+\]$", "", n)
isclk = lambda n: re.match(CLK_RE, base(n)) is not None
MACF = d / "core_macros.json"; CM = json.loads(MACF.read_text())
CEF = d / "clock_entries.json"; CE = json.loads(CEF.read_text()) if CEF.exists() else {}
CCF = d / "core_conns.json"; CC = json.loads(CCF.read_text()) if CCF.exists() else {}
event = dict(schema="opentallas.hbm_split_event.v1", cores=[])
OPP = dict(N="S", S="N", E="W", W="E")


def compose(a, b):                     # orient of a sub (b, in the core frame) in a core placed with orient a
    fx = (a in ("MY", "R180")) != (b in ("MY", "R180")); fy = (a in ("MX", "R180")) != (b in ("MX", "R180"))
    return {(0, 0): "R0", (1, 0): "MY", (0, 1): "MX", (1, 1): "R180"}[(int(fx), int(fy))]


def to_sub(o, f, x, y, w, h):          # tile-relative core-frame face + point -> sub-frame face + point
    if o in ("MX", "R180"):
        y = h - y; f = OPP[f] if f in "NS" else f
    if o in ("MY", "R180"):
        x = w - x; f = OPP[f] if f in "EW" else f
    return f, x, y


def natkey(n):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", n)]


def tf_face(o, f):                     # core-frame face -> type-frame face
    if o in ("MX", "R180") and f in "NS": f = OPP[f]
    if o in ("MY", "R180") and f in "EW": f = OPP[f]
    return f


def tf_pt(o, x, y, W, H):              # core-frame point -> placed-core frame
    return (W - x if o in ("MY", "R180") else x), (H - y if o in ("MX", "R180") else y)


def face_of(x, y, W, H, tol=0.5):
    ds = dict(W=x, E=W - x, S=y, N=H - y)
    f = min(ds, key=ds.get)
    return f if ds[f] <= tol else None


def tiles_1d(W, H, cells, mir):
    """different subs along the long axis; every tile start on the lattice in R0, every tile end on the lattice of the
    mirrored frame (mir: some instance is mirrored on that axis), street >= ST_MIN."""
    ax = 0 if W >= H else 1
    L = (W, H)[ax]; n = len(cells); tot = sum(cells); free = L - G * (n - 1)
    a, spans, acc = 0.0, [], 0.0
    for i in range(n - 1):
        acc += cells[i]
        a_n = snap(acc / tot * free + G * i + G)                     # next start (lattice)
        b = (r3(L - math.ceil((L - (a_n - ST_MIN)) / G - 1e-6) * G) if mir[ax] else r3(a_n - G))
        spans.append((a, b)); a = a_n
    spans.append((a, L))
    return [([s, 0.0], [r3(e - s), H]) if ax == 0 else ([0.0, s], [W, r3(e - s)]) for s, e in spans]


def tiles_rep(W, H, n):
    """identical replicas: equal tiles along the long axis, abutted when the slot divides on the lattice."""
    ax = 0 if W >= H else 1
    L = (W, H)[ax]
    t = L / n
    if abs(t / G - round(t / G)) < 1e-6:
        st = 0.0
    else:
        t = math.floor(((L - ST_MIN * (n - 1)) / n) / G + 1e-6) * G
        st = math.floor(((L - n * t) / (n - 1)) / PITCH + 1e-6) * PITCH
    sp = [(r3(i * (t + st)), r3(t)) for i in range(n)]
    return [([s, 0.0], [w, H]) if ax == 0 else ([0.0, s], [W, w]) for s, w in sp]


def dist_box(px, py, o, wh):
    return max(o[0] - px, 0, px - (o[0] + wh[0])) + max(o[1] - py, 0, py - (o[1] + wh[1]))


def outer_faces(o, wh, W, H):
    f = []
    if o[0] <= 1e-6: f.append("W")
    if o[0] + wh[0] >= W - 1e-6: f.append("E")
    if o[1] <= 1e-6: f.append("S")
    if o[1] + wh[1] >= H - 1e-6: f.append("N")
    return f


def toward(o, wh, po, pwh):
    cx, cy = o[0] + wh[0] / 2, o[1] + wh[1] / 2; px, py = po[0] + pwh[0] / 2, po[1] + pwh[1] / 2
    if abs(px - cx) >= abs(py - cy):
        return "E" if px > cx else "W"
    return "N" if py > cy else "S"


def legalize(items, length, lo=1.0):
    """items [(want, key)] on one face -> ({key: coord} on tracks, order kept, every 2nd track when it fits), ok."""
    if not items:
        return {}, True
    items = sorted(items)
    hi = length - lo
    for s in (2 * PITCH, PITCH):
        if (hi - lo) / s + 1 >= len(items):
            break
    else:
        return None, False
    pos = []
    for w, _ in items:
        p = trk(min(max(w, lo), hi))
        if pos and p < pos[-1] + s - 1e-9:
            p = r3(pos[-1] + s)
        pos.append(p)
    for i in range(len(pos) - 1, -1, -1):
        lim = trk(hi) if i == len(pos) - 1 else r3(pos[i + 1] - s)
        if pos[i] > lim + 1e-9:
            pos[i] = lim
    return {k: p for (_, k), p in zip(items, pos)}, True


def entry_pins(names, ex, ey):
    """clock_entry_pins / plan_clock_entries placement: every 2nd M5 track centred on the entry x."""
    cx = OFF + math.floor((ex - OFF) / PITCH + 0.5) * PITCH
    k0 = -((len(names) - 1) // 2)
    return {n: (r3(cx + (k0 + i) * 2 * PITCH), r3(ey)) for i, n in enumerate(sorted(names, key=lambda n: (base(n), n)))}


cores = {}            # core -> state used by the later passes
for sp in SPEC:
    core = sp["core"]
    if only and core not in only:
        continue
    insts = [(tn, i, h) for tn, t in P["partition_types"].items() for i, h in enumerate(t.get("hard_cores") or [])
             if h["module"] == core]
    if not insts:
        event["cores"].append(dict(core=core, status="NOT IN PLAN")); continue
    W, H = (r3(v) for v in insts[0][2]["outline_um"])
    assert all(r3(h["outline_um"][0]) == W and r3(h["outline_um"][1]) == H for _, _, h in insts), core
    ors = {h.get("orient", "R0") for _, _, h in insts}
    mir = (bool(ors & {"MY", "R180"}), bool(ors & {"MX", "R180"}))
    OP = {p["name"]: p for p in json.loads((d / sorted({h["pins_file"] for _, _, h in insts})[0]).read_text())}
    C = json.loads((SD / sp["conn"]).read_text())
    subs = C["subs"]
    mod_of = {s["inst"]: s["module"] for s in subs}
    cells = {s["module"]: s["cells"] for s in sp["subs"]}
    names = [s["inst"] for s in subs]
    lay = sp.get("layout")
    best = None
    if lay:
        assert set(lay) == set(names), (core, sorted(set(lay) ^ set(names)))
        for n_, v_ in lay.items():
            for c_ in (v_["xy"][0], v_["xy"][1], W - v_["xy"][0] - v_["wh"][0], H - v_["xy"][1] - v_["wh"][1]):
                assert c_ >= -1e-6 and abs(c_ / G - round(c_ / G)) < 1e-6, (core, n_, "tile edge off the lattice", c_)
        best = (0.0, {n_: (list(v_["xy"]), list(v_["wh"])) for n_, v_ in lay.items()})
    for perm in ([] if lay else [names] if sp.get("replicas") else itertools.permutations(names)):
        bx = tiles_rep(W, H, len(perm)) if sp.get("replicas") else tiles_1d(W, H, [cells[mod_of[n]] for n in perm], mir)
        tb = dict(zip(perm, bx))
        cost = 0.0
        for s in subs:
            o, wh = tb[s["inst"]]
            for b in s["bits"].values():
                cost += sum(dist_box(OP[t]["x"], OP[t]["y"], o, wh) for t in b["top"] if t in OP)
                for q in b["peer"]:
                    po, pwh = tb[q]
                    cost += abs(o[0] + wh[0] / 2 - po[0] - pwh[0] / 2) + abs(o[1] + wh[1] / 2 - po[1] - pwh[1] / 2)
        if best is None or cost < best[0] - 1e-6:
            best = (cost, tb)
    tb = best[1]
    sub_or = {n_: (lay[n_].get("orient", "R0") if lay else "R0") for n_ in names}
    tag = {s["inst"]: s["inst"].split(".")[-1].removeprefix("u_") for s in subs}
    rep = collections.OrderedDict()
    for s in subs:
        rep.setdefault(s["module"], []).append(s["inst"])
    # clock entry per sub module (sub frame)
    entry = {}
    for mod, ins in rep.items():
        w, h = tb[ins[0]][1]
        assert all(tb[i][1] == tb[ins[0]][1] for i in ins), (core, mod, "replica tiles differ")
        e = (sp.get("clock_entry") or {}).get(mod) or [snap(w / 2, PG), snap(h / 2, PG)]
        entry[mod] = (r3(e[0]), r3(e[1]))
    # wanted pin sites per sub inst (tile frame)
    want = {}
    for s in subs:
        o, wh = tb[s["inst"]]; w, h = wh; of = outer_faces(o, wh, W, H)
        wm = want[s["inst"]] = {}
        for nm, b in s["bits"].items():
            if isclk(nm):
                wm[nm] = ("C", None); continue
            tops = [OP[t] for t in b["top"] if t in OP]
            if tops:
                fs = [face_of(p["x"], p["y"], W, H) for p in tops]
                x = sum(p["x"] for p in tops) / len(tops) - o[0]; y = sum(p["y"] for p in tops) / len(tops) - o[1]
                if all(f is None for f in fs):
                    f = min(of or list("NSEW"), key=lambda F: dict(W=abs(x), E=abs(w - x), S=abs(y), N=abs(h - y))[F])
                else:
                    f = max(set(f for f in fs if f), key=fs.count)
                    if f not in of and not sp.get("keep_face"):
                        f = min(of or list("NSEW"), key=lambda F: dict(W=abs(x), E=abs(w - x), S=abs(y), N=abs(h - y))[F])
                f, x, y = to_sub(sub_or[s["inst"]], f, x, y, w, h)
                wm[nm] = (f, (x, y))
            elif b["peer"]:
                q = next((p_ for p_ in b["peer"] if p_ == sp.get("hub_sub")), b["peer"][0]); po, pwh = tb[q]
                f = toward(o, wh, po, pwh)
                if lay:
                    f = "N" if po[1] + pwh[1] / 2 > o[1] + h / 2 else "S"
                    lo_, hi_ = max(o[0], po[0]), min(o[0] + w, po[0] + pwh[0])
                    f, m, _ = to_sub(sub_or[s["inst"]], f, (lo_ + hi_) / 2 - o[0], 0.0, w, h)
                    wm[nm] = (f, (m, 0.0), q if len(rep[s["module"]]) == 1 else mod_of[q])
                    continue
                if f in "WE":
                    lo_, hi_ = max(o[1], po[1]), min(o[1] + h, po[1] + pwh[1]); m = ((lo_ + hi_) / 2 - o[1])
                    wm[nm] = (f, (0.0, m), q)
                else:
                    lo_, hi_ = max(o[0], po[0]), min(o[0] + w, po[0] + pwh[0]); m = ((lo_ + hi_) / 2 - o[0])
                    wm[nm] = (f, (m, 0.0), q)
            else:
                wm[nm] = ("F", None)
    cores[core] = dict(sp=sp, insts=insts, W=W, H=H, subs=subs, tb=tb, tag=tag, rep=rep, entry=entry, want=want,
                       cost=best[0], force={(m_, b_): f_ for m_, v_ in (sp.get("sub_face") or {}).items() for b_, f_ in v_.items()},
                       sub_or=sub_or, lay=bool(lay))


def build_tables(core):
    S = cores[core]; tb, rep, entry, force = S["tb"], S["rep"], S["entry"], S["force"]
    tables = {}
    for mod, ins in rep.items():
        o, wh = tb[ins[0]]; w, h = wh
        bits = list(next(s for s in S["subs"] if s["inst"] == ins[0])["bits"])
        faces = {f: [] for f in "NSEW"}; clk = []; free = []
        shared = [(c_, i_) for c_, S_ in cores.items() for i_ in S_["rep"].get(mod, [])]
        for c_, i_ in shared:
            assert cores[c_]["tb"][i_][1] == wh, (mod, c_, i_, "shared master outline differs")
            assert sorted(next(s for s in cores[c_]["subs"] if s["inst"] == i_)["bits"]) == sorted(bits), (mod, c_, "ports")
            assert tuple(cores[c_]["entry"][mod]) == tuple(entry[mod]), (mod, c_, "clock entry differs")
        for nm in bits:
            ws = [cores[c_]["want"][i_][nm] for c_, i_ in shared]
            kinds = [x[0] for x in ws]
            k = max(set(kinds), key=kinds.count)
            sel = [x for x in ws if x[0] == k]
            if k == "C":
                clk.append(nm); continue
            if k == "F":
                free.append(nm); continue
            x = sum(v[1][0] for v in sel) / len(sel); y = sum(v[1][1] for v in sel) / len(sel)
            f = force.get((mod, base(nm)), k)
            faces[f].append(((x if f in "NS" else y), nm, len(sel[0]) > 2 and f == k, sel[0][2] if len(sel[0]) > 2 else None))
        # seam pins: per face, in name order around the shared-edge midpoint (both ends use the same order)
        for f in faces:
            sm = [it for it in faces[f] if it[2]]
            if sm and S["lay"]:
                # one block per peer, in natural bit order, centred on the peer and packed without overlap
                L, grp = (w if f in "NS" else h), collections.defaultdict(list)
                for c_, nm, _, q_ in sm:
                    grp[q_].append((c_, nm))
                blocks = sorted((sum(c_ for c_, _ in v) / len(v), q_, sorted((nm for _, nm in v), key=natkey)) for q_, v in grp.items())
                st_, placed, end = 2 * PITCH, [], 0.0
                for mid, _, nms in blocks:
                    a_ = max(mid - st_ * len(nms) / 2, end)
                    placed.append((a_, nms)); end = a_ + st_ * len(nms)
                over = max(0.0, end - (L - 1.0))
                seam = []
                for a_, nms in placed:
                    seam += [(a_ - over + st_ * j, nm) for j, nm in enumerate(nms)]
                faces[f] = [it[:2] for it in faces[f] if not it[2]] + seam
                continue
            if sm:
                mid = sum(it[0] for it in sm) / len(sm); span = 2 * PITCH * len(sm)
                order = {nm: j for j, nm in enumerate(sorted(it[1] for it in sm))}
                faces[f] = [it for it in faces[f] if not it[2]] + [(mid - span / 2 + 2 * PITCH * order[it[1]], it[1], True) for it in sm]
            faces[f] = [it[:2] for it in faces[f]]
        def sub_outer(c_, i_):
            S_ = cores[c_]
            return {to_sub(S_["sub_or"][i_], f_, 0.0, 0.0, 1.0, 1.0)[0] for f_ in outer_faces(*S_["tb"][i_], S_["W"], S_["H"])}
        of = [f for f in "NSEW" if all(f in sub_outer(c_, i_) for c_, i_ in shared)] or list("NSEW")
        for nm in free:
            f = min(of, key=lambda F: len(faces[F]) / (w if F in "NS" else h))
            faces[f].append(((w if f in "NS" else h) / 2, nm))
        pins, ring = [], ["N", "E", "S", "W"]
        for f in ring:
            L = w if f in "NS" else h
            res, ok = legalize(faces[f], L)
            while not ok:                                       # spill the far end to the next face clockwise
                faces[f].sort(); mv = faces[f].pop()
                faces[ring[(ring.index(f) + 1) % 4]].append((0.0, mv[1]))
                res, ok = legalize(faces[f], L)
            for nm, c in res.items():
                pins.append(dict(N=dict(name=nm, layer="M5", x=c, y=r3(h - EDGE)), S=dict(name=nm, layer="M5", x=c, y=EDGE),
                                 E=dict(name=nm, layer="M4", x=r3(w - EDGE), y=c), W=dict(name=nm, layer="M4", x=EDGE, y=c))[f])
        for nm, (x, y) in entry_pins(clk, *entry[mod]).items():
            pins.append(dict(name=nm, layer="M5", x=x, y=y, w=0.048, h=0.48))
        assert len({p["name"] for p in pins}) == len(bits) == len(pins), (core, mod)
        fn = f"cores/{mod}__{w:g}x{h:g}__d44v_split.json"
        (d / fn).write_text(json.dumps(pins) + "\n")
        fc = collections.Counter(face_of(p["x"], p["y"], w, h) or "I" for p in pins)
        tables[mod] = dict(pins_file=fn, outline_um=[w, h], pins=len(pins), clock_pins=len(clk),
                           clock_entry=list(entry[mod]), faces=dict(sorted(fc.items())))
    S["tables"] = tables
    return tables


def nearest(cands, xy, boxes):
    def dd(sname):
        (x0, y0, w, h) = boxes[sname]
        return dist_box(xy[0], xy[1], (x0, y0), (w, h)) if xy else 0.0
    return min(cands, key=lambda c: (dd(c), c))


# ---------------------------------------------------------------- swap + sidecars
for core, S in cores.items():
    build_tables(core)
    sp, tb, subs, tag, W, H = S["sp"], S["tb"], S["subs"], S["tag"], S["W"], S["H"]
    clkb = {s["inst"]: sorted({base(nm) for nm in s["bits"] if isclk(nm)}) for s in subs}
    clkn = {s["inst"]: sorted(nm for nm in s["bits"] if isclk(nm)) for s in subs}
    portmap = {}      # sub inst -> top base -> Counter(sub bit base)
    for s in subs:
        pm = portmap[s["inst"]] = collections.defaultdict(collections.Counter)
        for nm, b in s["bits"].items():
            for t in b["top"]:
                pm[base(t)][base(nm)] += 1
    n_st = collections.Counter(); S["placed"] = []
    for tn, i, h in sorted(S["insts"], key=lambda x: (x[0], -x[1])):
        T = P["partition_types"][tn]
        hc = T["hard_cores"]
        i = next(k for k, x in enumerate(hc) if x["inst"] == h["inst"])    # earlier swaps of this pass shift the indices
        old = hc.pop(i)
        I = old["inst"]; ox, oy = old["origin_um"]; orr = old.get("orient", "R0")
        ox, oy = ox + old.get("track_offset_um", [0.0, 0.0])[0], oy + old.get("track_offset_um", [0.0, 0.0])[1]
        new, boxes = [], {}
        for s in subs:
            (x0, y0), (w, hh) = tb[s["inst"]]
            if orr in ("MY", "R180"): x0 = W - x0 - w
            if orr in ("MX", "R180"): y0 = H - y0 - hh
            X, Y = ox + x0, oy + y0
            so = compose(orr, S["sub_or"][s["inst"]])
            gx, gy = round(X / G) * G, round(Y / G) * G               # nearest lattice point, |offset| < 2.16
            sn = f"{I}__{tag[s['inst']]}"
            boxes[sn] = (X, Y, w, hh)
            e = dict(inst=sn, module=s["module"], origin_um=[r3(gx), r3(gy)], outline_um=[w, hh],
                     track_offset_um=[r3(X - gx), r3(Y - gy)], pins_file=S["tables"][s["module"]]["pins_file"],
                     physical_inst=f"{I}.{s['inst']}", physical_master=s["module"],
                     note=f"DIE-HBM-61/SPLIT d44v p6: sub-core {s['inst']} of {core} (SPLIT {sp['sha']}; glue {sp['glue']})")
            if so != "R0": e["orient"] = so
            if "obs_max" in old: e["obs_max"] = old["obs_max"]
            st = old.get("parent_id_straps")
            if st:
                mine = {}
                for k, v in st.items():
                    sb = portmap[s["inst"]].get(k)
                    if sb:
                        sk = sb.most_common(1)[0][0]
                        mine[sk] = dict(v)
                if mine: e["parent_id_straps"] = mine
            new.append(e)
        hc[i:i] = new
        sub_of = {s["inst"]: f"{I}__{tag[s['inst']]}" for s in subs}
        S["placed"].append((tn, I, orr, sub_of, boxes))
        # clock entries + taps
        ce_t = CE.setdefault(tn, {}); oe = ce_t.pop(I, None) or {}
        taps = (T.get("clock") or {}).get("taps") or []
        otaps = [tp for tp in taps if tp.get("name") == I or str(tp.get("name", "")).startswith(I + ".")]
        ot = otaps[0] if otaps else None
        keep_taps = [tp for tp in taps if tp not in otaps]
        for s in subs:
            sn = sub_of[s["inst"]]; mod = s["module"]
            cb, cn = clkb[s["inst"]], clkn[s["inst"]]
            if not cb:
                continue
            ex, ey = S["entry"][mod]
            tname = sn + ("." + cb[0] if (ot and "." in ot["name"] and len(cb) == 1) else "")
            ent = {k: v for k, v in oe.items() if k not in ("xy_um", "island_um", "port", "merged_clock_ports", "tap",
                                                             "module", "native_module", "clock_bind_contract")}
            ent.update(xy_um=[ex, ey], island_um=[r3(ex - PG), r3(ey - PG), r3(ex + PG), r3(ey + PG)],
                       port=cb[0] if len(cb) == 1 else None, merged_clock_ports=cb if len(cb) > 1 else [],
                       tap=tname, module=mod, native_module=mod,
                       source=(oe.get("source", "") + " | " if oe else "") +
                       f"DIE-HBM-61/SPLIT p6: sub-core centre entry of {I} (4.32 PG lattice, sub frame)")
            ce_t[sn] = ent
            if ot:
                (bx, by, bw, bh) = boxes[sn]
                px, py = tf_pt(compose(orr, S["sub_or"][s["inst"]]), ex, ey, bw, bh)
                tp = {k: v for k, v in ot.items() if k not in ("merged_clock_ports",)}
                tp.update(name=tname, xy=[r3(bx + px), r3(by + py)],
                          note=f"DIE-HBM-61/SPLIT p6: sub-core tap of {I} (was {ot['name']}) | " + ot.get("note", "")[:200])
                if ot.get("merged_clock_ports") and len(cn) > 1:
                    tp["merged_clock_ports"] = cn
                keep_taps.append(tp)
        if T.get("clock") is not None and otaps:
            T["clock"]["taps"] = keep_taps
        # internal stations
        memo = {}
        st_sub = sp.get("boundary_sub")     # the sub that owns the core's outer interface (bus-level station refs)
        def remap(ref, xy):
            if not isinstance(ref, str) or not (ref == I or ref.startswith(I + ".")):
                return ref
            key = (ref, tuple(xy) if xy else None)
            if key in memo:
                return memo[key]
            if ref == I:
                out = sub_of[st_sub] if st_sub else nearest(list(boxes), xy, boxes)
            else:
                p = ref[len(I) + 1:]
                cands = {sub_of[s["inst"]]: portmap[s["inst"]][p] for s in subs if portmap[s["inst"]].get(p)}
                if cands:
                    mx = max(sum(c.values()) for c in cands.values())
                    sn = nearest([k for k, c in cands.items() if sum(c.values()) == mx], xy, boxes)
                    out = sn + "." + cands[sn].most_common(1)[0][0]
                else:
                    out = (sub_of[st_sub] if st_sub else nearest(list(boxes), xy, boxes)) + "." + p; n_st["dead-port"] += 1
            memo[key] = out
            return out
        for stn in T.get("internal_stations") or []:
            fx, tx_ = stn.get("from_um"), stn.get("to_um")
            ch = False
            for fld, xy in (("launch", fx), ("capture", tx_)):
                if fld in stn:
                    nv = remap(stn[fld], xy); ch |= nv != stn[fld]; stn[fld] = nv
            if isinstance(stn.get("conn"), str) and not stn["conn"].startswith("bus:") and "|" in stn["conn"]:
                a, b = stn["conn"].split("|", 1)
                na, nb = remap(a, fx), remap(b, tx_)
                ch |= (na, nb) != (a, b); stn["conn"] = f"{na}|{nb}"
            n_st["stations"] += ch
        # core_conns
        cct = CC.get(tn)
        if cct is not None:
            oc = cct.pop(I, {})
            for s in subs:
                sn = sub_of[s["inst"]]; m = collections.defaultdict(set)
                for nm, b in s["bits"].items():
                    sb = base(nm)
                    for t in b["top"]:
                        for v in oc.get(base(t), []):
                            m[sb].add(("tap:" + sn) if v == "tap:" + I else v)
                    for q in ([] if isclk(nm) else b["peer"]):      # a shared clock is a tap net, not a seam
                        m[sb].add("core:" + sub_of[q])
                if m:
                    cct[sn] = {k: sorted(v) for k, v in sorted(m.items())}
            for ci, ports in cct.items():
                if ci in sub_of.values():
                    continue
                for lp, lst in ports.items():
                    if "core:" + I in lst:
                        hit = ([sub_of[s["inst"]] for s in subs if portmap[s["inst"]].get(lp)] or
                               ([sub_of[sp["boundary_sub"]]] if sp.get("boundary_sub") else list(sub_of.values())))
                        ports[lp] = sorted((set(lst) - {"core:" + I}) | {"core:" + x for x in hit})
    S["stations"] = dict(n_st)
    for mod, mm in (S["sp"].get("macros") or {}).items():
        w, h = S["tables"][mod]["outline_um"]
        for a in mm:
            x0, y0, x1, y1 = a["rect_um"]
            assert x0 >= 4.32 and y0 >= 4.32 and x1 <= w - 4.32 and y1 <= h - 4.32, (mod, a)
            ex, ey = S["entry"][mod]
            assert not (x0 - PG < ex < x1 + PG and y0 - PG < ey < y1 + PG), (mod, "clock entry on a macro", a)
        CM["cores"][mod] = dict(status="KNOWN", outline_um=[w, h], macros=mm, channel_rule_um=10.8,
                                basis=S["sp"].get("macro_basis", "DIE-HBM-61/SPLIT d44v part 6"))


def write_all():
    pp.unlink(); pp.write_text(json.dumps(P, indent=1) + "\n")
    for f, o in ((MACF, CM), (CEF, CE), (CCF, CC)):
        if f.exists():
            f.unlink()
        f.write_text(json.dumps(o, indent=1) + "\n")


write_all()
# ---------------------------------------------------------------- core_faces pass (check.py model, as mk_repin)
subset = {}
for core, S in cores.items():
    if S["lay"]:
        continue
    for tn, I, orr, sub_of, boxes in S["placed"]:
        for si, sn in sub_of.items():
            subset[(tn, sn)] = (core, next(s["module"] for s in S["subs"] if s["inst"] == si), orr, si)
rec = []
CK.check_core_faces(SC.Plan(json.loads(pp.read_text()), pp), CK.Report(True), str(d), collect=rec)
score = collections.defaultdict(lambda: collections.defaultdict(list))
bad = collections.defaultdict(list)
for r in rec:
    k = (r["type"], r["inst"])
    if k not in subset:
        continue
    core, mod, orr, si = subset[k]
    bad[(core, mod, r["port"])].append(r["mean"])
    for f in "NSEW":
        n_ = CK._NORMAL[tf_face(orr, f)]
        score[(core, mod, r["port"])][f].append(max(n_[0] * ux + n_[1] * uy for _, ux, uy in r["dirs"]))
moved = []
for (core, mod, port), means in bad.items():
    if min(means) >= CK.FACE_WARN_COS - 1e-9 and sum(means) / len(means) >= 0:
        continue
    S = cores[core]
    o, wh = S["tb"][S["rep"][mod][0]]
    of = outer_faces(o, wh, S["W"], S["H"]) or list("NSEW")
    sc = {f: sum(v) / len(v) for f, v in score[(core, mod, port)].items() if f in of}
    if not sc:
        continue
    bf = max(sc, key=sc.get)
    if any(port == base(nm) for nm in S["want"][S["rep"][mod][0]] if isclk(nm)):
        continue
    S["force"][(mod, port)] = bf
    moved.append(dict(core=core, module=mod, port=port, to=bf, mean_before=round(min(means), 3), score_after=round(sc[bf], 3)))
for core in {m["core"] for m in moved}:
    build_tables(core)
for core, S in cores.items():
    event["cores"].append(dict(core=core, sha=S["sp"]["sha"], status="SPLIT -> PLAN DESIGNS", glue=S["sp"]["glue"],
                               slot_um=[S["W"], S["H"]], instances=len(S["insts"]), types=sorted({t for t, _, _ in S["insts"]}),
                               tiles={s["inst"]: S["tb"][s["inst"]] for s in S["subs"]}, tables=S["tables"],
                               added_cycles=S["sp"].get("added_cycles"), pin_displacement_um=round(S["cost"], 1),
                               stations_repointed=S["stations"], designs_removed=[core], designs_added=sorted(S["tables"])))
old = json.loads((d / "split_event.json").read_text()) if (d / "split_event.json").exists() else dict(cores=[])
event["core_faces_moves"] = old.get("core_faces_moves", []) + moved
event["cores"] = [c for c in old.get("cores", []) if c["core"] not in cores] + event["cores"]
(d / "split_event.json").unlink(missing_ok=True); (d / "split_event.json").write_text(json.dumps(event, indent=1) + "\n")
for c in event["cores"]:
    print(c["core"], c["status"], c.get("instances"), {m: (t["outline_um"], t["pins"], t["faces"]) for m, t in c.get("tables", {}).items()},
          c.get("stations_repointed"))
print("core_faces moves", [(m["module"][-12:], m["port"], m["to"]) for m in moved])
