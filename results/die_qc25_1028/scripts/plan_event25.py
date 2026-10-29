#!/usr/bin/env python3
"""DIE-QC-25 plan event ev_qc25 = ev_qc24 (e12e39da0fae) with the E-column SU crh cores on the RTL's module.

COORD 10-28 22:32 (DIE-QC-24 ASK2, TOK-QC-3 21:49): the ONE-QC RTL (qfd_dv_s8_vm8q_rp1) instantiates u_cl / u_ch as
qfd_dv_s8_crh_rp1 in EVERY slice, but the plan type sle_su_c (sl_E0..E5_su_c) still names qfd_dv_s8x_crh there (an older
CORELAT-SQ-1 early-tap pick, 259.2 x 276.48 um, insertion 292.49/240.62 ps).  The W types (slw_su_c__*) already carry the
signed crh_rp1 view (autopilot f4g 5ed4500430, 250.56 x 216 um, common latency 250 / 202.5 ps).  This event copies the W
crh_rp1 entries into sle_su_c at the SAME origins (crh_rp1 is smaller: it fits inside the old footprint, no overlap
change), so plan and bind come from one RTL lineage:
  contents[u_cl/u_ch], hard_cores[u_cl/u_ch]: module, outline_um, pins_file, note  <- slw_su_c__cl92142dac
  clock.taps u_cl.ck / u_ch.ck: xy = origin + (W pin offset), insertion / ff / budget_owner <- W (common latency)
Nothing else changes (asserted: only those keys differ).  The clock tree must be re-planned on ev_qc25 (the two E crh
taps move from early 292.49 to the common 250 ps target).
usage: plan_event25.py IN OUT"""
import copy
import hashlib
import json
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
P = json.loads(src.read_text())
T = P["partition_types"]
E, W = T["sle_su_c"], T["slw_su_c__cl92142dac"]
CRH = ("u_suvm_u_vm8q_u_cl", "u_suvm_u_vm8q_u_ch")
OLD, NEW = "qfd_dv_s8x_crh", "qfd_dv_s8_crh_rp1"


def by_inst(lst):
    return {x["inst"]: x for x in lst}


n = 0
for key in ("contents", "hard_cores"):
    we = by_inst(W[key])
    for x in E[key]:
        if x.get("inst") in CRH:
            assert x["module"] == OLD and we[x["inst"]]["module"] == NEW, (key, x["inst"])
            assert x["origin_um"] == we[x["inst"]]["origin_um"], "E/W crh origins differ"
            for k in ("module", "outline_um", "pins_file", "note", "status"):
                if k in we[x["inst"]]:
                    x[k] = copy.deepcopy(we[x["inst"]][k])
            n += 1
assert n == 4, n
wt = {t["name"]: t for t in W["clock"]["taps"]}
worg = {h["inst"]: h["origin_um"] for h in W["hard_cores"]}
eorg = {h["inst"]: h["origin_um"] for h in E["hard_cores"]}
m = 0
for t in E["clock"]["taps"]:
    inst = t["name"].rsplit(".", 1)[0]
    if inst in CRH:
        w = wt[t["name"]]
        off = [w["xy"][i] - worg[inst][i] for i in (0, 1)]
        t["xy"] = [round(eorg[inst][i] + off[i], 6) for i in (0, 1)]
        for k in ("insertion_ps", "insertion_tol_ps", "insertion_ff_ps", "budget_owner", "orient"):
            if k in w:
                t[k] = w[k]
        m += 1
assert m == 2, m
assert OLD not in json.dumps(T["sle_su_c"]), "s8x_crh still referenced in sle_su_c"
P["note"] = (P.get("note") or "") + " | DIE-QC-25 ev_qc25: sle_su_c u_cl/u_ch -> qfd_dv_s8_crh_rp1 (RTL lineage, W view copied)"
dst.write_text(json.dumps(P, indent=1) + "\n")
print("ev_qc25", hashlib.sha256(dst.read_bytes()).hexdigest()[:12], "from", hashlib.sha256(src.read_bytes()).hexdigest()[:12],
      "crh entries", n, "taps", m, "s8x_crh refs left in plan", json.dumps(P).count(OLD))
