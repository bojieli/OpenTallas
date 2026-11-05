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
import itertools, json, re, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]

M = "ot_v41_rom_elem_q_qxpq_w10_gb"
LEF = Path(f"physical/die_plan/s81/cores/elem_boundary/{M}.lef")
W0, H0, D, GAP = 510.84, 221.4, 25.92, 4.32
W1 = round(W0 + D, 2)
src, out, rep = sys.argv[1:]
P = json.loads(Path(src).read_text())


def rect(h):
    (x, y), (w, hh) = h["origin_um"], h["outline_um"]
    return [x, y, x + w, y + hh]


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
    pts = [tuple(r) for s in t.get("internal_stations") or [] for r in s.get("regs_um", [])]
    pts += [tuple(q) for f in t.get("ft_slots") or [] for g in f.get("bit_sites_um", []) for q in g]
    best = None
    for combo in sorted(itertools.product((0, 1), repeat=len(idx)), key=sum):
        new = list(rects)
        for c, i in zip(combo, idx):
            r = rects[i]
            new[i] = [r[0] - D * c, r[1], r[2] + D * (1 - c), r[3]]
        ok = all(new[i][0] >= 0 and new[i][2] <= TW
                 and not any(j != i and near(new[i], o, GAP) for j, o in enumerate(new))
                 and not any(inside(q, new[i]) for q in pts) for i in idx)
        if ok:
            best = combo
            break
    assert best is not None, f"{tn}: no legal growth"
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
            assert not any(inside(q, r) for r in allr), (tn, inst, q)
    report["types"][tn] = {"dirs": "".join("-" if c else "+" for c in best), "moved": moved,
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
report["n_instances"] = sum(len(v["insts"]) for v in report["types"].values())
Path(rep).write_text(json.dumps(report, indent=1) + "\n")
print(json.dumps({k: report[k] for k in ("n_types", "n_instances", "n_moved")}))
