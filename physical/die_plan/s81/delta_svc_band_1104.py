#!/usr/bin/env python3
"""S81 svc macro band plan event (DIE-S81-56/PLAN 11-04, COORD 07:34 (5): svc rows + MEM v2 c4a9eee3064 + band = ONE plan
event).  Replayable on top of any plan_h2_2249.json that still has the 2453.76-um svc rows; a second run refuses.

Form (estimate in results/die_s81_56_svc_1104/README.md):
  * every svc_lo type grows G_LO, every svc_hi type grows G_HI in Y.  Hard cores, taps, ft stations below the top hcore
    row keep their type-local coordinates.  The band opens between the top hcore row (top 2410.56) and the N strip;
    everything above Y_CUT (N strip: landing bands, relays, N-face clock pins, N-strip ft sites) moves up by G with
    its N face.
  * partitions above each svc row shift up, die outline +G_LO+G_HI (25.36 mm <= 26 mm reticle), die io / pg / seal /
    free-cell rects and the clock spine root follow.
  * the 14 non-svc columns get NO spacer partitions: the N/S ports across the two gaps become planned die.channels
    (schema: between + ports + layers + width_um), 2-pin seam nets on M7/M5/M3 across the gap.  Non-svc types keep
    type-local coordinates, pins and keys.  Reset wave: reset.in_sites + reset.parent_pins + reset.keep_outs hold every non-svc
    parent and out as solved on the base plan; 11 parents go out of hop across the shifted rows and re-home, and 5 non-svc
    types (non_svc_trees_changed in the output) take one new rst_o out, so their reset trees re-solve and their kits relaunch.
  * contents[] macro sites in the band for the MEM v2 macros + the glue macros the plan never placed, per
    delta_svc_band_1104.json (place_sites below; 2.16 lattice + per-master track offset, >= 10.8 channels, 43.2 W/E edge).

usage: delta_svc_band_1104.py SRC_PLAN OUT_PLAN MACROS_JSON SRC_SIDECAR OUT_SIDECAR
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import pin_template as PT  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema as S  # noqa: E402

G_LO, G_HI = 319.68, 293.76
H0 = 2453.76
Y_CUT = 2411.0
HCORE_TOP = 2410.56
Y0_BAND = HCORE_TOP + 10.8
EDGE_X = 43.2
CH = 10.8
LAT = 2.16
LO_TOP, HI_TOP = 3784.32, 6238.08
TAG = "DIE-S81-56/PLAN 11-04 svc band site (delta_svc_band_1104.py)"
TRK = {"M4": ("H", 0.048, 0.024, (0.024,)), "M5": ("V", 0.048, 0.024, (0.024,)), "M6": ("H", 0.064, 0.032, (0.032,)),
       "M7": ("V", 0.064, 0.032, (0.032,)), "M3": ("V", 0.036, 0.018, (0.009,)),
       "M2": ("H", 0.270, 0.018, (0.045, 0.081, 0.117, 0.153, 0.189, 0.225, 0.270))}
POINT_KEYS = {"xy", "xy_um", "tap_um", "pin_xy_um", "root"}
LIST_KEYS = {"regs_um", "bit_sites_um"}
RECT_KEYS = {"rect_um"}
RECTS_KEYS = {"rects_um"}


def lef_info(lef):
    t = (ROOT / lef).read_text()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
    pins = []
    for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\b", t, re.M | re.S):
        if re.search(r"\bUSE\s+(POWER|GROUND)\b", pm.group(2)):
            continue
        layer = None
        for tok in re.finditer(r"LAYER\s+(\S+)\s*;|RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", pm.group(2)):
            if tok.group(1):
                layer = tok.group(1)
            elif layer in TRK:
                pins.append((layer, *map(float, tok.groups()[1:])))
    return (float(m.group(1)), float(m.group(2))), pins


def on_grid(pins, ox, oy):
    for layer, x0, y0, x1, y1 in pins:
        d, p, w, offs = TRK[layer]
        lo, hi = (oy + y0, oy + y1) if d == "H" else (ox + x0, ox + x1)
        ok = False
        for of in offs:
            c = (lo + hi) / 2
            t = of + round((c - of) / p) * p
            if any(lo + w / 2 - 5e-4 <= tt <= hi - w / 2 + 5e-4 for tt in (t - p, t, t + p)):
                ok = True
        if not ok:
            return False
    return True


def track_offset(pins):
    for k in range(0, 40):
        for dx in (0.0, 0.108, 0.216, 0.324, 0.432):
            dy = round(0.012 * k, 3)
            if on_grid(pins, dx, dy):
                return dx, dy
    raise SystemExit("no on-grid offset")


def up(v):
    n = int(v / LAT)
    return round((n if abs(n * LAT - v) < 1e-6 else n + 1) * LAT, 3)


def place_sites(rows, masters):
    """rows = bottom-to-top [[(inst, module), ...], ...]; returns sites and the band top."""
    sites, y = [], up(Y0_BAND)
    x_max = 1442.88 - EDGE_X
    for row in rows:
        x, h = EDGE_X, 0.0
        for inst, mod in row:
            (w, hh), dxy = masters[mod]["size"], masters[mod]["off"]
            assert x + w <= x_max + 1e-6, ("row too wide", mod, x)
            sites.append(dict(inst=inst, module=mod, status="new", lef=masters[mod]["lef"], lib=masters[mod]["lib"],
                              origin_um=[round(x + dxy[0], 3), round(y + dxy[1], 3)], outline_um=[w, hh], orient="R0",
                              obs_max="M4", note=TAG))
            x = up(x + w + CH)
            h = max(h, hh)
        y = up(y + h + CH)
    return sites, round(y - CH, 3)


def rows_for(macs):
    """macs [(inst, module)] -> rows, by function bottom to top: attn staging + PMEM next to the attn hcores, LAND, PVQ,
    idx, CDC.  Order inside a row is the sorted instance name (deterministic, stable under replay)."""
    def of(*names):
        return sorted(m for m in macs if m[1] in names)
    rows = [of("ot_sram_1r1w_160x265_m1_r0c0") + [m for m in of("ot_sram_1r1w_256x256_m1_r0c0") if "u_irg" not in m[0]],
            of("ot_sram_1r1w_160x256_m1_r0c0"),
            of("ot_sram_1r1w_32x128_m1_r0c0") + [m for m in of("ot_sram_1r1w_32x64_m1") if "ingress" not in m[0]]]
    ing = [m for m in of("ot_sram_1r1w_32x64_m1") if "ingress" in m[0]]     # pvso_entry: 136 P.V ingress macros
    rows += [ing[i:i + 31] for i in range(0, len(ing), 31)]
    idx = [m for m in of("ot_sram_1r1w_256x256_m1_r0c0") if "u_irg" in m[0]]
    p192 = sorted(m for m in macs if "p192" in m[1])
    if idx or p192:
        rows.append(of("ot_sram_1r1w_768x256_m2_r0c0") + idx)
        rows.append(p192 + of("ot_sram_1r1w_1024x35_m4_r0c0", "ot_sram_1r1w_1024x39_m4_r0c0", "ot_sram_1r1w_128x23_m1_r0c0"))
    n = sum(len(r) for r in rows)
    assert n == len(macs), ("macro with no row", n, len(macs), sorted({m[1] for m in macs}))
    return rows


def shift_type(t, G):
    """move everything of the N strip (type-local y > Y_CUT) up by G; a rect that straddles Y_CUT stretches."""
    n = [0]

    def walk(o, key=None):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in POINT_KEYS and isinstance(v, list) and len(v) == 2 and all(isinstance(a, (int, float)) for a in v):
                    if v[1] > Y_CUT:
                        v[1] = round(v[1] + G, 4)
                        n[0] += 1
                elif k in LIST_KEYS:
                    pts(v)
                elif k in RECT_KEYS and isinstance(v, list) and len(v) == 4:
                    rect(v)
                elif k in RECTS_KEYS:
                    for r in v:
                        rect(r)
                else:
                    walk(v, k)
        elif isinstance(o, list):
            for v in o:
                walk(v, key)

    def pts(v):
        if len(v) == 2 and all(isinstance(a, (int, float)) for a in v):
            if v[1] > Y_CUT:
                v[1] = round(v[1] + G, 4)
                n[0] += 1
        else:
            for q in v:
                pts(q)

    def rect(r):
        if r[1] > Y_CUT:
            r[1], r[3] = round(r[1] + G, 4), round(r[3] + G, 4)
            n[0] += 1
        elif r[3] > Y_CUT:
            r[3] = round(r[3] + G, 4)
            n[0] += 1
    walk(t.get("clock", {}))
    walk(t.get("reset", {}))
    walk(t.get("ft_slots", []))
    for s in t.get("ft_slots", []):
        for f, w in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
            if s[f] in "WE":
                assert max(s[w]) <= Y_CUT, (s["name"], "W/E ft window in the N strip")
    for b in t["buses"]:
        if b.get("face") in ("W", "E") and "window_um" in b:
            assert max(b["window_um"]) <= Y_CUT, (b["name"], "W/E bus window in the N strip")
    for c in t.get("hard_cores", []):
        assert c["origin_um"][1] + c["outline_um"][1] <= Y_CUT, c["inst"]
    return n[0]


def shift_sidecar(src, out, svc, dy, G_of):
    """landed sidecar: region boxes follow their partitions; collector geometry of the svc types follows the N strip"""
    T = json.loads(Path(src).read_text())
    for r in T["regions"]:
        b = r["box_um"]
        g = max((G_of.get(p, 0.0) for p in r["parts"]), default=0.0)
        b[1], b[3] = round(b[1] + dy(b[1]), 4), round(b[3] + dy(b[3] - 0.02) + g, 4)
    n = [0]

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            nums = len(o) in (2, 4) and all(isinstance(a, (int, float)) and not isinstance(a, bool) for a in o)
            if not nums:
                for v in o:
                    walk(v)
            elif len(o) == 2 and o[1] > Y_CUT:
                o[1] = round(o[1] + G, 4)
                n[0] += 1
            elif len(o) == 4 and o[3] > Y_CUT:
                if o[1] > Y_CUT:
                    o[1] = round(o[1] + G, 4)
                o[3] = round(o[3] + G, 4)
                n[0] += 1
    for k in svc:
        G = G_LO if k.startswith("svc_lo") else G_HI
        walk(T["collector"]["types"][k])
    Path(out).write_text(json.dumps(T, separators=(",", ":")))
    return n[0]


def plan_text(P):
    """repo plan format with one line per collector_tree relay row (results/rf_eg_1104/compact_relays.py: 45 MB, not 106 MB)"""
    txt = PT.dumps(P)
    dec, res, last = json.JSONDecoder(), [], 0
    for m in re.finditer(r'(?m)^( +)"relays": \[', txt):
        i = m.end() - 1
        v, e = dec.raw_decode(txt, i)
        pad = m.group(1) + " "
        body = "[]" if not v else "[\n" + ",\n".join(pad + json.dumps(r, separators=(",", ":")) for r in v) + "\n" + m.group(1) + "]"
        res += [txt[last:i], body]
        last = e
    res.append(txt[last:])
    new = "".join(res)
    assert json.loads(new) == P, "whitespace edit changed the plan"
    return new


def publish_tree(lc, st, tree, rep):
    """write a re-solved reset tree to the plan landing contract and the sidecar type; collector sources name taps of the
    published tree, so re-pick them like clock_landing_plan (nearest tap to the pin, else band centre)."""
    tapxy = {r["q"]: r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
    near_tap = lambda xy: min(tapxy, key=lambda q: abs(tapxy[q][0] - xy[0]) + abs(tapxy[q][1] - xy[1]))
    dist = lambda q, xy: abs(tapxy[q][0] - xy[0]) + abs(tapxy[q][1] - xy[1])
    for holder, skey, ckey in ((lc, "collector_local_sources", "collector_children"), (st, "local_sources", "children")):
        for row in holder.get(skey) or ():
            if row.get("tap") is None:
                continue
            pin = row.get("pin_xy_um") or row["xy_um"]
            q = near_tap(pin)
            rect = (row.get("band") or {}).get("rect_um")
            if dist(q, pin) > 405 and rect:
                pin = [round((rect[0] + rect[2]) / 2, 3), round((rect[1] + rect[3]) / 2, 3)]
                q = near_tap(pin)
            row["tap"], row["xy_um"] = int(q.split("rst_n_t")[1]), pin
            rep["max_source_hop_um"] = round(max(rep.get("max_source_hop_um", 0), dist(q, pin)), 1)
        for kid in holder.get(ckey) or ():
            if "node" in kid:
                kid["node"] = near_tap(kid["xy_um"])
                rep["max_source_hop_um"] = round(max(rep.get("max_source_hop_um", 0), dist(kid["node"], kid["xy_um"])), 1)
    if lc.get("collector_tree"):
        lc["collector_tree"] = tree
    if st.get("tree"):
        st["tree"] = tree


def main():
    src, out, macros, side_src, side_out = sys.argv[1:6]
    S0 = Path(src).read_text()
    Psch = S.Plan(S.load(src))
    P = json.loads(S0)
    pt, parts = P["partition_types"], P["partitions"]
    assert P["die"]["outline_um"][1] == 24744.96, "not the pre-event die (second run?)"
    svc = sorted(k for k in pt if k.startswith("svc_"))
    assert len(svc) == 16 and all(pt[k]["outline_um"][1] == H0 for k in svc), "svc rows not in the pre-event form"

    def dy(y):
        return (G_LO if y >= LO_TOP - 0.01 else 0.0) + (G_HI if y >= HI_TOP - 0.01 else 0.0)
    # channels: N/S ports across each cut outside the svc columns, one channel per partition pair
    xl, xr = 10203.84, 21746.88
    pairs = {}
    for pid, q in Psch.ports.items():
        a, b = q["src"]["part"], q["dst"]["part"]
        if "@die" in (a, b) or q.get("face") not in ("N", "S"):
            continue
        ra, rb = Psch.rect(a), Psch.rect(b)
        for c, g in ((LO_TOP, G_LO), (HI_TOP, G_HI)):
            lo, hi = (a, b) if abs(ra[3] - c) < 1e-3 and abs(rb[1] - c) < 1e-3 else \
                (b, a) if abs(rb[3] - c) < 1e-3 and abs(ra[1] - c) < 1e-3 else (None, None)
            if lo is None or (xl - 1 < max(ra[0], rb[0]) and min(ra[2], rb[2]) < xr + 1):
                continue
            pairs.setdefault((lo, hi, g), []).append(pid)
    assert len(pairs) == 28, len(pairs)
    # geometry
    shift = {}
    for p in parts:
        d = dy(p["origin_um"][1])
        shift[p["name"]] = d
        if d:
            p["origin_um"][1] = round(p["origin_um"][1] + d, 3)
    nw = 0
    for q in P["ports"]:
        if q.get("face") in ("W", "E") and "window_um" in q:
            end = q["src"]["part"] if q["src"]["part"] in shift else q["dst"]["part"]
            d = shift.get(end, 0.0)
            if d:
                q["window_um"] = [round(v + d, 3) for v in q["window_um"]]
                nw += 1
    die = P["die"]
    Hnew = round(die["outline_um"][1] + G_LO + G_HI, 3)

    def shift_rects(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "rect_um" and len(v) == 4:
                    d = dy(v[1])
                    assert dy(v[3] - 0.02) == d, ("rect straddles a cut", v)
                    v[1], v[3] = round(v[1] + d, 4), round(v[3] + d, 4)
                else:
                    shift_rects(v)
        elif isinstance(o, list):
            for v in o:
                shift_rects(v)
    shift_rects(die["io"])
    DOM_RECTS = {"phy_macro_um", "esd_um", "exclude_um", "bump_exclude_um", "core_strip_um"}

    def shift_named(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in DOM_RECTS:
                    for r in ([v] if v and isinstance(v[0], (int, float)) else v):
                        d = dy(r[1])
                        assert dy(r[3] - 0.02) == d, ("rect straddles a cut", k, r)
                        r[1], r[3] = round(r[1] + d, 4), round(r[3] + d, 4)
                else:
                    shift_named(v)
        elif isinstance(o, list):
            for v in o:
                shift_named(v)
    shift_named(die["io"])
    shift_named(die["pg"]["domains"])
    shift_rects(die["pg"]["domains"])
    Htop = die["outline_um"][1] - 103.68
    for c in die["channels"]:
        r = c["rect_um"]
        if r[1] < 103.69 and r[3] > Htop - 1:      # W/E seal ring: stretch
            r[3] = round(r[3] + G_LO + G_HI, 4)
        elif r[3] > 104:                           # top seal ring, free cells above the rows
            d = dy(r[1])
            r[1], r[3] = round(r[1] + d, 4), round(r[3] + d, 4)
    die["outline_um"][1] = Hnew
    r = P["clock"]["spine"]["root_um"]
    r[1] = round(r[1] + dy(r[1]), 3)
    for (lo, hi, g), ids in sorted(pairs.items()):
        die["channels"].append(dict(name=f"svcband_{lo}__{hi}", between=[lo, hi], ports=sorted(ids), width_um=g,
                                    layers=["M7", "M5", "M3"],
                                    reason="S81 svc band gap (delta_svc_band_1104): no partition, seam nets cross on die route"))
    # svc types
    M = json.loads(Path(macros).read_text())
    masters = {}
    for mod, e in M["masters"].items():
        size, pins = lef_info(e["lef"])
        masters[mod] = dict(lef=e["lef"], lib=e["lib"], size=list(size), off=track_offset(pins))
    report = {}
    for k in svc:
        G = G_LO if k.startswith("svc_lo") else G_HI
        t = pt[k]
        moved = shift_type(t, G)
        ins = P["reset"]["in_sites"].get(k)
        if ins and ins[1] > Y_CUT:
            ins[1] = round(ins[1] + G, 4)
        t["outline_um"][1] = round(t["outline_um"][1] + G, 3)
        sites, top = place_sites(rows_for([tuple(x) for x in M["types"][k]]), masters)
        n_top = min(HCORE_TOP + 8.64 + G, H0 + G)  # lowest N-strip item
        assert top + CH <= 2419.2 + G + 1e-6 or top + CH <= n_top + 1e-6, (k, "band overruns the N strip", top, G)
        t["contents"] = t["contents"] + sites
        t["note"] = t.get("note", "") + f" | svc band +{G} um Y (delta_svc_band_1104): {len(sites)} macro sites to y {top}"
        report[k] = dict(G=G, moved=moved, sites=len(sites), band_top=top)
    P["note"] = P["note"] + f" | S81 svc band 11-04: svc_lo +{G_LO}, svc_hi +{G_HI} um Y, die +{G_LO + G_HI} um, 28 die channels, MEM v2 macro sites"
    Path(out).write_text(plan_text(P))
    G_of = {p["name"]: (G_LO if p["type"].startswith("svc_lo") else G_HI) for p in parts if p["type"].startswith("svc_")}
    side_moved = shift_sidecar(side_src, side_out, svc, dy, G_of)
    # the band stretched the svc reset trees: publish what the solver gives on the new geometry (bind re-solves; a moved
    # tree that is not the solved one fails EMIT collector), plan and sidecar alike (results/rf_eg_1104/republish_trees.py)
    # keep the reset wave of every non-svc partition as solved on the base plan: the band only lengthens svc trees, but
    # those later releases flip Dijkstra races and IN-site picks and would rewrite the reset trees of 22 non-svc types.
    B = S.Plan(S.load(src), src)
    W0 = RT.wf_solve(B)
    P["reset"]["in_sites"].update({tn: list(xy) for tn, xy in W0["choice"].items() if not tn.startswith("svc_")})
    nons = lambda k: not k.startswith("svc_")
    Pg = S.Plan(json.loads(plan_text(P)), out)
    hp = RT.hop_um(B) - RT.MARGIN_UM
    in_xy = lambda p: RT.part_reset_pin(Pg, p) if p in W0["hard"] else Pg.to_die(p, W0["choice"][Pg.parts[p]["type"]])
    sites_of = lambda q: [(j, Pg.to_die(q, s_["xy"])) for j, s_ in enumerate(RT.face_sites(Pg, Pg.parts[q]["type"]))]
    man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
    pins = {p: pr[0] for p, pr in W0["parent"].items() if pr is not None and nons(Pg.parts[p]["type"])}
    broken = sorted(p for p, q in pins.items() if min(man(xy, in_xy(p)) for _, xy in sites_of(q)) > hp + 1e-6)
    for p in broken:
        del pins[p]
    kids = {}
    for p, q in pins.items():
        kids.setdefault(q, []).append(p)
    def below(p):
        seen, todo = {p}, [p]
        while todo:
            for c in kids.get(todo.pop(), ()):
                if c not in seen:
                    seen.add(c)
                    todo.append(c)
        return seen
    rehomed, free = {}, []
    for p in broken:  # the out of hop edges: an out the parent type already has (or any svc site); else the solver's pick
        below_p, opts = below(p), []
        for q in Pg.parts:
            if q in W0["hard"] or q in below_p:
                continue
            tq = Pg.parts[q]["type"]
            for j, xy in sites_of(q):
                if man(xy, in_xy(p)) <= hp + 1e-6 and (not nons(tq) or j in W0["outs"].get(tq, [])):
                    opts.append((round(man(xy, in_xy(p)), 1), q, j))
        if opts:
            _, q, j = min(opts)
            pins[p] = [q, j]
            rehomed[p] = q
            kids.setdefault(q, []).append(p)
        else:
            free.append(p)
    P["reset"]["parent_pins"] = dict(sorted(pins.items()))
    W1 = RT.wf_solve(S.Plan(json.loads(plan_text(P)), out))
    keep = {k: sorted(set(W0["outs"][k]) - set(W1["outs"][k])) for k in W0["outs"] if nons(k) and set(W0["outs"][k]) - set(W1["outs"][k])}
    P["reset"]["keep_outs"] = keep
    Path(out).write_text(plan_text(P))
    Pn = S.Plan(S.load(out), out)
    changed = sorted(k for k in B.types if not B.types[k].get("hard") and nons(k)
                     and (lambda a, b: a["relays"] != b["relays"] or a.get("outs") != b.get("outs"))(RT.for_type(B, k), RT.for_type(Pn, k)))
    report.update({k: {} for k in changed})
    T = json.loads(Path(side_out).read_text())
    for k in list(svc) + changed:
        tree = json.loads(json.dumps(RT.for_type(Pn, k)))
        lc = pt[k]["clock"].get("landing_contract") or {}
        st = T["collector"]["types"].get(k) or {}
        old = lc.get("collector_tree") or st.get("tree") or RT.for_type(B, k)
        report[k].update(reset_depth=[old["depth"], tree["depth"]], relays=[len(old["relays"]), len(tree["relays"])],
                         published=[bool(lc.get("collector_tree")), bool(st.get("tree"))])
        publish_tree(lc, st, tree, report[k])
    C = T["collector"]
    for p in parts:
        if p["type"] in report and p["name"] in C["boot_budget"]["local_registered_depths"]:
            C["boot_budget"]["local_registered_depths"][p["name"]] += report[p["type"]]["reset_depth"][1] - report[p["type"]]["reset_depth"][0]
    W1, W_old = RT.wf_plan(Pn), RT.wf_plan(B)
    C["reset_max_release"] += W1["max_release"] - W_old["max_release"]
    C["boot_budget"]["raw_reset_release_max_cycles"] += W1["max_release"] - W_old["max_release"]
    Path(side_out).write_text(json.dumps(T, separators=(",", ":")))
    Path(out).write_text(plan_text(P))
    print(json.dumps(dict(side_moved=side_moved, non_svc_trees_changed=changed, parent_pins=len(pins), wave_edges_out_of_hop=broken, rehomed=rehomed, solver_parents=free,
                          keep_outs=keep, unreachable=RT.wf_solve(Pn)["unreachable"],
                          wave_max_release=[W_old["max_release"], W1["max_release"]], G_LO=G_LO, G_HI=G_HI, die=die["outline_um"], ew_windows=nw, channels=len(pairs),
                          channel_bits=sum(len(v) for v in pairs.values()), types=report), indent=0))


if __name__ == "__main__":
    main()
