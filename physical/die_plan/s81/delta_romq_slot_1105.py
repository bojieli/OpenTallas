#!/usr/bin/env python3
"""S81 plan event ROMQ-SLOT (DIE-S81-64 11-05, COORD 15:04 ruling): rom_q core ot_v41_rom_elem_q_qxpq_w10_gb +25.92 um wide.

Why: rfk1/romq forms sit at stdcell util ~0.47 in 502.2x212.76 core area (222k cells, 4 ROM macros); romq1 i2 missed
(FF -2.49/1, DRV 17), romq2 DRT-1231, rq3a (density 0.50, same outline) stopped at GRT OT_HOLD_STRUCTURAL FF -184.62/2204.
+25.92 um width -> stdcell util ~0.447 (<= 0.45 conservative target).  Master 510.84 x 221.4 -> 536.76 x 221.4.

All 737 pins sit on the S/N faces at master x 151.2..508.84, so pins keep their master coordinates.  The new strip is the
master's east 25.92 um.  Per type (26 types, 104 instances) each instance either keeps its origin (grows east, '+') or
moves its origin 25.92 um west ('-', pins move -25.92 in the parent) -- the combination with the fewest moves that keeps
>= GAP um to every other hard core, stays inside the type outline and covers no internal-station register or ft bit site.
A moved instance carries its clock core tap xy and its collector reset leaf (pin_um, xy) by the same -25.92 um.
LEF: SIZE widened; existing OBS kept; the new strip is blocked M1-M7 (obs_max M7) until the rebuilt core's abstract lands.
    python3 delta_romq_slot_1105.py PLAN_IN PLAN_OUT REPORT_JSON      (cwd = repo root)
"""
import itertools, json, math, re, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
from placement_obstacles import placement_boxes  # noqa: E402

M = "ot_v41_rom_elem_q_qxpq_w10_gb"
LEF = Path(f"physical/die_plan/s81/cores/elem_boundary/{M}.lef")
W0, H0, D, GAP = 510.84, 221.4, 25.92, 4.32
CLR = 8.64 - 1e-6      # schema.TAP_CLEAR_UM (taps.py: a tap exactly at the halo edge is legal)
W1 = round(W0 + D, 2)
src, out, rep = sys.argv[1:]
P = json.loads(Path(src).read_text())


def rect(h):
    """placed footprint as schema.placed_macro_boxes sees a hard core (track offset applied once)"""
    (x, y), (w, hh) = h["origin_um"], h["outline_um"]
    dx, dy = h.get("track_offset_um", [0.0, 0.0])
    return [x + dx, y + dy, x + dx + w, y + dy + hh]


def near(a, b, g):
    return a[0] < b[2] + g and b[0] < a[2] + g and a[1] < b[3] + g and b[1] < a[3] + g


def core_resets(t, inst):
    """collector reset leaf of inst (types without a landing contract have none)"""
    lc = t["clock"].get("landing_contract") or {}
    return [x for x in (lc.get("collector_tree") or {}).get("core_resets") or [] if x["inst"] == inst]


def inside(q, r):
    return r[0] < q[0] < r[2] and r[1] < q[1] < r[3]


report = {"event": "ROMQ-SLOT-1105", "module": M, "master_um": [[W0, H0], [W1, H0]], "types": {}}
for tn, t in P["partition_types"].items():
    hcs = t.get("hard_cores") or []
    idx = [i for i, h in enumerate(hcs) if h.get("module") == M]
    if not idx:
        continue
    assert all(hcs[i]["outline_um"] == [W0, H0] and hcs[i].get("orient", "R0") == "R0" for i in idx), tn
    TW, TH = t["outline_um"]
    rects = [rect(h) for h in hcs]
    roms = {hcs[i]["inst"] for i in idx}
    # every other physical obstacle as G0/G2 see it (hard cores, LEF contents, physical parts, probe blockages)
    others = [b for n, b in placement_boxes(t).items() if n not in roms]
    pts = [tuple(r) for s in t.get("internal_stations") or [] for r in s.get("regs_um", [])]
    pts += [tuple(q) for f in t.get("ft_slots") or [] for g in f.get("bit_sites_um", []) for q in g]
    ck = t.get("clock") or {}
    # added clock taps (taps.grid_explicit_sites: >= TAP_CLEAR_UM off every core) that the grown core would cover move
    # out along x to the new halo edge, with the reset relays sited on them (same tap id, same xy)
    added = ck.get("added_taps") or []
    assert ck.get("tap_mode") in (None, "grid", "grid+explicit"), (tn, ck.get("tap_mode"))
    TC = CLR + 1e-6

    def tap_plan(new):
        """tap moves needed by the grown rectangles `new`, or None when a tap cannot move to a legal site"""
        halo = [[r[0] - CLR, r[1] - CLR, r[2] + CLR, r[3] + CLR] for r in (new[i] for i in idx)]
        obst = [[o[0] - CLR, o[1] - CLR, o[2] + CLR, o[3] + CLR] for o in others] + halo
        moves, fixed = {}, [tuple(map(float, x["xy"])) for x in added]
        for k, x in enumerate(added):
            q = tuple(map(float, x["xy"]))
            hit = [h for h in halo if inside(q, h)]
            if not hit:
                continue
            h = hit[0]
            nx = math.ceil((h[2] + 1e-6) * 1000) / 1000 if q[0] - h[0] > h[2] - q[0] else math.floor((h[0] - 1e-6) * 1000) / 1000
            nq = (nx, q[1])
            if not (CLR <= nx <= TW - CLR) or any(inside(nq, o) for o in obst) or \
                    any(abs(nq[0] - f[0]) < CLR and abs(nq[1] - f[1]) < CLR for j, f in enumerate(fixed) if j != k):
                return None
            moves[k] = nq
            fixed[k] = nq
        return moves

    best = None
    for combo in itertools.product((0, 1), repeat=len(idx)):
        new = list(rects)
        for c, i in zip(combo, idx):
            r = rects[i]
            new[i] = [r[0] - D * c, r[1], r[2] + D * (1 - c), r[3]]
        ok = all(new[i][0] >= 0 and new[i][2] <= TW
                 and not any(j != i and j in idx and near(new[i], o, GAP) for j, o in enumerate(new))
                 and not any(near(new[i], o, GAP) for o in others)
                 and not any(inside(q, new[i]) for q in pts) for i in idx)
        tm = tap_plan(new) if ok else None
        if tm is None:
            continue
        cost = (len(tm), sum(combo))
        if best is None or cost < best[0]:
            best = (cost, combo, tm)
    assert best is not None, f"{tn}: no legal growth"
    _, best, tmoves = best
    lc = ck.get("landing_contract") or {}
    relays = (lc.get("collector_tree") or {}).get("relays") or []
    tapmoved = []
    for k, nq in tmoves.items():
        old = list(map(float, added[k]["xy"]))
        tid = int(added[k]["name"][len("clk_t"):])     # taps.grid_explicit_sites: added taps follow the grid, by name
        added[k]["xy"] = [nq[0], added[k]["xy"][1]]
        rl = [r for r in relays if r.get("tap") == tid and list(map(float, r["xy"])) == old]
        for r in rl:
            r["xy"] = [nq[0], r["xy"][1]]
        tapmoved.append({"tap": added[k]["name"], "from": old, "to": added[k]["xy"], "relays": [r["name"] for r in rl]})
    moved = []
    for c, i in zip(best, idx):
        h = hcs[i]
        h["outline_um"] = [W1, H0]
        h["note"] = (h.get("note", "") + " | ROMQ-SLOT-1105 DIE-S81-64: master +25.92 um wide"
                     + (", origin -25.92 um (grows west)" if c else " (grows east)")).lstrip(" |")
        if not c:
            continue
        h["origin_um"] = [round(h["origin_um"][0] - D, 3), h["origin_um"][1]]
        inst = h["inst"]
        taps = [x for x in t["clock"]["taps"] if x["name"].startswith(inst + ".")]
        assert len(taps) == 1, (tn, inst, taps)
        taps[0]["xy"] = [round(taps[0]["xy"][0] - D, 3), taps[0]["xy"][1]]
        crs = core_resets(t, inst)
        assert len(crs) <= 1, (tn, inst)
        for x in crs:
            for k in ("pin_um", "xy"):
                x[k] = [round(x[k][0] - D, 3), x[k][1]]
        moved.append(inst)
    allr = [rect(h) for h in hcs]
    for i in idx:   # moved tap / reset leaf points must not land inside another hard core
        inst = hcs[i]["inst"]
        for q in [x["xy"] for x in t["clock"]["taps"] if x["name"].startswith(inst + ".")] + \
                 [x["xy"] for x in core_resets(t, inst)]:
            # 0.02 um tolerance: base core taps already sit on a neighbour's edge before its 0.012 track offset
            assert not any(inside(q, [r[0] + .02, r[1] + .02, r[2] - .02, r[3] - .02]) for r in allr), (tn, inst, q)
    report["types"][tn] = {"dirs": "".join("-" if c else "+" for c in best), "moved": moved, "taps_moved": tapmoved,
                           "insts": [hcs[i]["inst"] for i in idx]}

# text edits inside the changed type blocks only (hard_cores are one line per row; tap / reset xy keep their layout)
text = Path(src).read_text()
num = r"-?[0-9.]+(?:e-?[0-9]+)?"
for n, info in report["types"].items():
    m = re.search('^  "' + re.escape(n) + '": ', text, re.M)
    _, j = json.JSONDecoder().raw_decode(text, m.end())
    blk = text[m.end():j]
    t = P["partition_types"][n]
    for h in t["hard_cores"]:
        if h.get("module") != M:
            continue
        pat = re.compile(r'(?m)^( *)\{"inst":"' + re.escape(h["inst"]) + r'","module":"' + M + r'".*?\}(,?)$')
        assert len(pat.findall(blk)) == 1, (n, h["inst"])
        blk = pat.sub(lambda q: q.group(1) + json.dumps(h, separators=(",", ":")) + q.group(2), blk)
    for inst in info["moved"]:
        tap = next(x for x in t["clock"]["taps"] if x["name"].startswith(inst + "."))
        pat = re.compile(r'("name": "' + re.escape(tap["name"]) + r'",\s*"kind": "core",\s*"xy": \[\s*)(' + num + ')')
        assert len(pat.findall(blk)) == 1, (n, inst, "tap")
        blk = pat.sub(lambda q: q.group(1) + json.dumps(tap["xy"][0]), blk)
        for cr in core_resets(t, inst):
            for k in ("pin_um", "xy"):
                pat = re.compile(r'("inst": "' + re.escape(inst) + r'",(?:(?!"inst").)*?"' + k + r'": \[\s*)(' + num + ')', re.S)
                assert pat.search(blk), (n, inst, k)
                blk = pat.sub(lambda q: q.group(1) + json.dumps(cr[k][0]), blk, count=1)
    for tmv in info["taps_moved"]:
        pat = re.compile(r'("name": "' + tmv["tap"] + r'",\s*"xy": \[\s*)(' + num + ')')
        assert len(pat.findall(blk)) == 1, (n, tmv["tap"])
        blk = pat.sub(lambda q: q.group(1) + json.dumps(tmv["to"][0]), blk)
        tid = int(tmv["tap"][5:])
        for rn in tmv["relays"]:
            pat = re.compile(r'(\{"name":"' + re.escape(rn) + r'","xy":\[)(' + num + r')(,[^\]]*\][^\n]*"tap":' + str(tid) + r',)')
            assert len(pat.findall(blk)) == 1, (n, rn)
            blk = pat.sub(lambda q: q.group(1) + json.dumps(tmv["to"][0]) + q.group(3), blk)
    text = text[:m.end()] + blk + text[j:]
assert json.loads(text) == P, "text edit does not reproduce the plan"
Path(out).write_text(text)
s = LEF.read_text()
assert s.count(f"SIZE {W0} BY {H0} ;") == 1
s = s.replace(f"SIZE {W0} BY {H0} ;", f"SIZE {W1} BY {H0} ;")
strip = "".join(f"    LAYER M{k} ;\n     RECT  {W0} 0 {W1} {H0} ;\n" for k in range(1, 8))
i = s.index("  OBS\n") + len("  OBS\n")
s = s[:i] + "    # ROMQ-SLOT-1105: new east strip blocked M1-M7 until the rebuilt abstract lands\n" + strip + s[i:]
LEF.write_text(s)
report["n_types"] = len(report["types"])
report["n_moved"] = sum(len(v["moved"]) for v in report["types"].values())
report["n_taps_moved"] = sum(len(v["taps_moved"]) for v in report["types"].values())
report["n_instances"] = sum(len(v["insts"]) for v in report["types"].values())
Path(rep).write_text(json.dumps(report, indent=1) + "\n")
print(json.dumps({k: report[k] for k in ("n_types", "n_instances", "n_moved", "n_taps_moved")}))
