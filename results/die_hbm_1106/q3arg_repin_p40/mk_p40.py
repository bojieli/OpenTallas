#!/usr/bin/env python3
"""DIE-HBM-82 d44v part 40 (COORD 11-06 13:37 RULINGS (1) + DIE-HBM-81 plan-owner ruling 13:37): q3_edge_arg same-slot re-pin.

Every ot_hfd_coll_q3_edge_arg hard core (today one: q_hub_nw u_hb_coll_Q_edge__q0__arg) takes the HBM-GAPS-8 re-pin table
(sha256 9ae65807400d..., made by physical/die_plan/hbm/over_cap_split/reform_1106/q3_edge_arg_repin/repin_q3_edge_arg.py
from the d44v_split table; HBM-GAPS-8 6edc0ba242), copied byte for byte into d44v/cores/.  Only the 547 S-face M5 pins
(y = 0.096) move along x inside the S face (spread 8.664-267.816); outline, origin, orient, track offset, the 425 E-face M4
pins and the centre clk pin (= clock entry 138.24,21.6) are unchanged.  The plan stores no parent-side copy of these pin
positions (core_conns are by pin name, the clock tap / clock entry is the unchanged core centre), so nothing else moves.
Gate: vA on this table ROUTED GRT0 / DRC 0 / ant 0 (epyc5 /srv/opentallas-scratch2/claude/hbm-gaps-8/q3/
ot_hfd_coll_q3_edge_arg_vA/ot_hfd_coll_q3_edge_arg_9ae65807400d).
    mk_p40.py REPO   (writes d44v/cores/<new table> + d44v/die_plan.json.gz, gzip mtime 0)"""
import gzip, hashlib, json, sys
from pathlib import Path
R = Path(sys.argv[1])
D = R / "physical/die_plan/hbm/plan_of_record/d44v"
SRC = R / "physical/die_plan/hbm/over_cap_split/reform_1106/q3_edge_arg_repin/ot_hfd_coll_q3_edge_arg__276.48x43.2__d44v_repin_hg8.json"
SHA = "9ae65807400d45d04ed4a58bc918bb80a9066c00769d96d81812f7c65ee4080a"
OLD = "cores/ot_hfd_coll_q3_edge_arg__276.48x43.2__d44v_split.json"
NEW = "cores/ot_hfd_coll_q3_edge_arg__276.48x43.2__d44v_repin_hg8.json"
b = SRC.read_bytes()
assert hashlib.sha256(b).hexdigest() == SHA, "re-pin table sha differs"
a_old, a_new = json.loads((D / OLD).read_text()), json.loads(b)
# pin check: same names; only S-face M5 pins (y 0.096) change, and only in x, staying inside the outline
o = {p["name"]: p for p in a_old}
n = {p["name"]: p for p in a_new}
assert set(o) == set(n) and len(o) == len(a_old) == len(a_new), "pin names differ"
moved = 0
for k, p in o.items():
    q = n[k]
    if p == q:
        continue
    assert p["layer"] == q["layer"] == "M5" and abs(p["y"] - 0.096) < 1e-9 and p["y"] == q["y"], (k, p, q)
    assert {x for x in p if p[x] != q.get(x)} == {"x"} and set(p) == set(q), (k, p, q)
    assert 0 < q["x"] < 276.48, (k, q)
    moved += 1
assert o["clk"] == n["clk"], "clk pin moved"
(D / NEW).write_bytes(b)
P = json.loads(gzip.decompress((D / "die_plan.json.gz").read_bytes()))
log = []
for tn, T in P["partition_types"].items():
    for h in T.get("hard_cores", []):
        if h.get("module") != "ot_hfd_coll_q3_edge_arg":
            continue
        assert h["pins_file"] == OLD and h["outline_um"] == [276.48, 43.2], (tn, h["inst"], h["pins_file"], h["outline_um"])
        h["pins_file"] = NEW
        h["note"] = (h.get("note", "") + " | DIE-HBM-82 d44v part 40: HBM-GAPS-8 same-slot re-pin table (S/M5 pins spread in x, "
                     "sha 9ae65807400d); outline/origin/E pins/clk unchanged").lstrip(" |")
        log.append((tn, h["inst"]))
assert len(log) >= 1, log
s = json.dumps(P)
assert OLD not in s
out = (s + "\n").encode()
with open(D / "die_plan.json.gz", "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
    g.write(out)
print("P40 pins moved (S/M5, x only)", moved, "of", len(a_new))
for x in log:
    print("P40", *x)
