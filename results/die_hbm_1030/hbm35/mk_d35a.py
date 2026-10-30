#!/usr/bin/env python3
"""DIE-HBM-35: plan event d35a = BASE (d32q) + SU lane_exp0_id outline option (a) (DIE-HBM-33 ruling 03:25, COORD 03:27).

ot_hbm_su_static_pgslice_lg__lane_exp0_id 440.64 x 207.36 (aspect 2.125, AUTO-GEOM FAIL) -> 414.72 x 207.36 (aspect 2.00),
SAME origin in q_su00 / q_su10 (MX) and their __physical_v1 twins (4 hard-core entries, 4 die instances).  The core only
shrinks, so no neighbour can overlap and no neighbour moves.  Pins (new file __414.72x207.36__d35a.json):
  * E face (840 M4): x 440.544 -> 414.624 (= W - 0.096), y unchanged.
  * W face: unchanged.
  * N face clock/reset cluster (clk_bank, clk_insert[*], clk_bank_macro[*], clk_lane[*], rst_lane_n; 20 pins, kept with
    their relative offsets and sizes) moves from the NW corner (x 2.3-31.4) to the N-face centre (around x 207.36 = the new
    centre clock entry).  The other N pins keep their order and are re-spaced over the face outside the cluster window.
  * S face: pins keep their order, x scaled into the narrower face; rst_n (partition reset entry, S face) moves to the
    S-face centre.  All x on the plan track grid (offset 0.024, pitch 0.048).
Clock: centre entry 12.8a stays the outline centre on the 4.32 PG lattice: (220.32, 103.68) -> (207.36, 103.68), island
[203.04, 99.36, 211.68, 108.0]; partition clock taps x -12.96 (R0 and MX alike), die tap tables likewise.
Partition internal_stations/regs that end on a moved pin are moved with it (exact match on the old parent coordinate).
Six 94.824 x 41.064 SRAMs (k2/k5 right edge 371.30) stay inside 414.72.  NEW files only (no write through hardlinks of BASE).
usage: mk_d35a.py BASE OUT"""
import json, subprocess, sys
from pathlib import Path

base, out = Path(sys.argv[1]), Path(sys.argv[2])
MOD = "ot_hbm_su_static_pgslice_lg__lane_exp0_id"
OLD = "cores/ot_hbm_su_static_pgslice_lg__lane_exp0_id__440.64x207.36__d31s.json"
NEW = "cores/ot_hbm_su_static_pgslice_lg__lane_exp0_id__414.72x207.36__d35a.json"
W0, W1, H = 440.64, 414.72, 207.36
G, OFF = 0.048, 0.024
EX0, EX1 = 220.32, 207.36
ISL = [203.04, 99.36, 211.68, 108.0]
TYPES = ["q_su00", "q_su10", "q_su00__physical_v1", "q_su10__physical_v1"]


def snap(x):
    return round(round((x - OFF) / G) * G + OFF, 3)


if out.exists():
    sys.exit(f"{out} exists (refuse to overwrite)")
subprocess.check_call(["cp", "-al", str(base), str(out)])


def wnew(rel, obj):
    p = out / rel
    if p.exists() or p.is_symlink():
        p.unlink()
    p.write_text(json.dumps(obj, indent=1) + "\n")


pins = json.load(open(base / OLD))
old = {q["name"]: dict(q) for q in pins}


def face(q):
    if abs(q["x"] - (W0 - 0.096)) < 0.2:
        return "E"
    if q["x"] < 0.2:
        return "W"
    if q["y"] > H - 0.5:
        return "N"
    if q["y"] < 0.2:
        return "S"
    raise SystemExit(f"pin not on a face: {q}")


F = {f: [q for q in pins if face(q) == f] for f in "NESW"}
for q in F["E"]:
    q["x"] = round(W1 - 0.096, 3)
# N face: clock/reset cluster to the centre, the rest re-spaced in order around it
clu = sorted([q for q in F["N"] if q["name"].startswith("clk") or q["name"].startswith("rst")], key=lambda q: q["x"])
rest = sorted([q for q in F["N"] if q not in clu], key=lambda q: q["x"])
c0, c1 = clu[0]["x"], clu[-1]["x"]
shift = round(round((EX1 - (c0 + c1) / 2) / G) * G, 3)
for q in clu:
    q["x"] = round(q["x"] + shift, 3)
win = (clu[0]["x"] - 1.0, clu[-1]["x"] + 1.0)
lo, hi = 2.328, snap(W1 - 2.328)
seg = [(lo, win[0]), (win[1], hi)]
L = sum(b - a for a, b in seg)
n = len(rest)
pitch = L / n
assert pitch >= 0.24, pitch
pos, t = [], 0.0
for i in range(n):
    s = i * pitch
    if s <= seg[0][1] - seg[0][0]:
        x = seg[0][0] + s
    else:
        x = seg[1][0] + s - (seg[0][1] - seg[0][0])
    pos.append(snap(x))
for q, x in zip(rest, pos):
    q["x"] = x
# S face: scaled in order, rst_n to the centre
srest = sorted([q for q in F["S"] if q["name"] != "rst_n"], key=lambda q: q["x"])
xs0 = [q["x"] for q in srest]
a0, b0 = xs0[0], xs0[-1]
for q in srest:
    q["x"] = snap(lo + (q["x"] - a0) * (hi - lo) / (b0 - a0))
rst = [q for q in F["S"] if q["name"] == "rst_n"]
assert len(rst) == 1
taken = sorted(q["x"] for q in srest)
x = snap(EX1)
k = 0
while any(abs(x - y) < 0.5 for y in taken):
    k += 1
    x = snap(EX1 + (k // 2 + 1) * G * (1 if k % 2 else -1))
rst[0]["x"] = x
# checks: unique positions per face, min pitch, inside outline
for f in "NS":
    v = sorted(q["x"] for q in F[f])
    gaps = [b - a for a, b in zip(v, v[1:])]
    assert min(gaps) >= 0.239, (f, min(gaps))
    assert v[0] > 0 and v[-1] < W1, (f, v[0], v[-1])
for q in pins:
    assert 0 <= q["x"] <= W1 and 0 <= q["y"] <= H
moved = {q["name"]: (old[q["name"]], q) for q in pins if (q["x"], q["y"]) != (old[q["name"]]["x"], old[q["name"]]["y"])}
wnew(NEW, pins)

P = json.load(open(base / "die_plan.json"))
nh = 0
nreg = 0
ntap = 0
for tn in TYPES:
    t = P["partition_types"][tn]
    hcs = [h for h in t.get("hard_cores", []) if h["module"] == MOD]
    assert len(hcs) == 1, (tn, len(hcs))
    h = hcs[0]
    assert h["pins_file"] == OLD and h["outline_um"] == [W0, H], h
    h["outline_um"] = [W1, H]
    h["pins_file"] = NEW
    h["note"] += (" | DIE-HBM-35 d35a: outline 440.64x207.36 -> 414.72x207.36 (aspect 2.00, AUTO-GEOM option (a), DIE-HBM-33"
                  " ruling 03:25 / COORD 03:27), same origin; clk/rst cluster at the N-face centre, rst_n S-face centre")
    ox, oy = h["origin_um"]
    mx = h.get("orient") == "MX"

    def par(q):
        return (round(ox + q["x"], 3), round(oy + (H - q["y"] if mx else q["y"]), 3))

    mp = {par(o): par(nq) for o, nq in moved.values()}

    def walk(v):
        global nreg
        if isinstance(v, list):
            if len(v) == 2 and all(isinstance(z, (int, float)) for z in v):
                for k_, nv in mp.items():
                    if abs(v[0] - k_[0]) < 0.002 and abs(v[1] - k_[1]) < 0.002:
                        nreg += 1
                        return [nv[0], nv[1]]
                return v
            return [walk(z) for z in v]
        if isinstance(v, dict):
            return {k_: walk(z) for k_, z in v.items()}
        return v

    for key in ("internal_stations", "buses", "die_ft_bands"):
        if key in t:
            t[key] = walk(t[key])
    for tp in t.get("clock", {}).get("taps", []):
        if tp.get("name") == h["inst"]:
            assert abs(tp["xy"][0] - (ox + EX0)) < 0.002, tp
            tp["xy"] = [round(ox + EX1, 3), tp["xy"][1]]
            ntap += 1
    nh += 1
assert nh == 4 and ntap == 4, (nh, ntap)
wnew("die_plan.json", P)

E = json.load(open(base / "entries.json"))
assert E[MOD]["xy"] == [EX0, 103.68]
E[MOD]["xy"] = [EX1, 103.68]
wnew("entries.json", E)
CE = json.load(open(base / "clock_entries.json"))
nce = 0
for tn in TYPES:
    for inst, e in CE.get(tn, {}).items():
        if e.get("module") == MOD:
            e["xy_um"] = [EX1, 103.68]
            e["island_um"] = ISL
            nce += 1
assert nce == 4, nce
wnew("clock_entries.json", CE)
ndt = 0
for f in ("clock_taps_die.json", "clock_taps_die.recomputed.json"):
    D = json.load(open(base / f))
    rows = D if isinstance(D, list) else D.get("taps", D)
    lst = rows if isinstance(rows, list) else []
    for r in lst:
        if isinstance(r, dict) and r.get("type") in TYPES and r.get("tap", "").endswith("_lane_exp0") and "xy_die_um" in r:
            r["xy_die_um"] = [round(r["xy_die_um"][0] - (EX0 - EX1), 3), r["xy_die_um"][1]]
            ndt += 1
    wnew(f, D)
rep = dict(lane="DIE-HBM-35", base=str(base), event="d35a SU lane_exp0_id outline option (a) 414.72x207.36", module=MOD,
           pins_file=NEW, old_pins_file=OLD, outline_um=[W1, H], aspect=round(W1 / H, 3), hard_core_entries=nh,
           pins=len(pins), pins_moved=len(moved), faces={f: len(v) for f, v in F.items()},
           n_cluster=[q["name"] for q in clu], cluster_x=[clu[0]["x"], clu[-1]["x"]], n_rest_pitch_um=round(pitch, 3),
           rst_n_x=rst[0]["x"], clock_entry_um=[EX1, 103.68], island_um=ISL, partition_taps_moved=ntap,
           die_tap_rows_moved=ndt, clock_entries_moved=nce, station_points_moved=nreg)
wnew("d35a_event_report.json", rep)
print(json.dumps(rep))
