# DIE-QC-58A (COORD 22:5x ruling (3) variant A): A0 frame event in the DIE-QC-18 form (mk_ev_a0meas.py). The declared A0
# insertion becomes the MEASURED ICG=2 value: MEDIAN input-face register clock arrival on the DIE-QC-57d V3 CTS tree
# (-balance_levels -wire_unit 25 -distance_between_buffers 100, reviewed rr1/rr2 3_place, setRC_rcx placement RC;
# meas58a.tcl): NK 841.5 TT / 668.3 FF, NL 849.1 TT / 672.1 FF (DIE-QC-18 median form; the max frame NK 745.2 FF
# moved the NK worst to R2O -169.7). The die taps every A0 core earlier by the delta to the DIE-QC-18 frame
# (NK +175.7/+91.8, NL +156.5/+70.2). Applied to the base plan_qc52 (re-running on an already-applied plan is idempotent). Values only: the 64 cb* A0 core taps in plan_qc52 and the
# qfd_tile_n{k,l}_a0c recipe frames (recipes_a0.json insertion_ps / insertion_ff_ps) that the kit generator binds.
#   python3 mk_ev_a0icg2.py PLAN_JSON RECIPES_JSON   (in place, formatting kept)
import json, sys
plan, rec = sys.argv[1], sys.argv[2]
W = "DIE-QC-58A measured ICG2 V3-CTS MEDIAN input-face register arrival, placement RC (DIE-QC-57d e6_nk/e3_nl tree)"
INS = {"qfd_tile_nk_a0c": (841.5, 668.3, "nk med58 " + W + "; FF face 583.3-745.2, max-frame 745.2 rejected: R2O -170"),
       "qfd_tile_nl_a0c": (849.1, 672.1, "nl med58 " + W + "; FF face 631.8-686.2")}
d = json.load(open(plan)); n = 0
for tn, t in d["partition_types"].items():
    mods = {h["inst"]: h["module"] for h in t.get("hard_cores", [])}
    for tp in t.get("clock", {}).get("taps", []):
        m = mods.get(tp["name"].split(".")[0], "")
        if tp.get("kind") != "core" or m not in INS:
            continue
        a, b, w = INS[m]
        tp["insertion_ps"], tp["insertion_ff_ps"] = a, b
        tp["budget_owner"] = "A0 frame event (" + w + "; COORD 22:5x (3) A, DIE-QC-18 form)"
        n += 1
if n != 64:
    raise SystemExit(f"expected 64 A0 core taps, found {n}")
open(plan, "w").write(json.dumps(d) + "\n")
r = json.load(open(rec))
for m, (a, b, w) in INS.items():
    r[m]["insertion_ps"], r[m]["insertion_ff_ps"] = a, b
    r[m]["insertion_basis"] = ("A0 frame event: kit IO frame = " + w + "; COORD 22:5x (3) A. Replaces the 12.3 wrapper "
                               "frame 250/202.5; the die taps the A0 entry EARLY by (frame - routed die-tap insertion).")
open(rec, "w").write(json.dumps(r, indent=1) + "\n")
print("taps", n, "recipes", sorted(INS))
