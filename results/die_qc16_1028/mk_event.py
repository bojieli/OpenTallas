# DIE-QC-16: derived event = qc_k2b_phase12.json with the c_* A0 core taps made EARLY (clock.core_taps="early") at
# their own ROUTED A0 parent-trunk insertion (DIE-QC-15 abb5f93ce7: nk q6 736/639, nl q3 796/694; COORD 11:43 (2) ASK 2).
import json, hashlib, sys
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src)); T = d["partition_types"]
INS = {"qfd_tile_nk_a0c": (736.0, 639.0, "nk routed q6 DIE-QC-15 abb5f93ce7"),
       "qfd_tile_nl_a0c": (796.0, 694.0, "nl routed q3 DIE-QC-15 abb5f93ce7")}
nt = ntap = 0
for tn, t in T.items():
    if not tn.startswith("cb"):
        continue
    mods = {h["inst"]: h["module"] for h in t["hard_cores"]}
    c = t["clock"]; ch = False
    for tp in c["taps"]:
        if tp.get("kind") != "core":
            continue
        a, b, why = INS[mods[tp["name"].split(".")[0]]]
        tp["insertion_ps"], tp["insertion_ff_ps"] = a, b
        tp["budget_owner"] = ("DIE-QC-16 A0 centre-entry early tap = own ROUTED A0 parent-trunk insertion (" + why +
                              "; COORD 11:43 (2) ASK 2 ACCEPTED)")
        ntap += 1; ch = True
    if ch:
        c["core_taps"] = "early"; nt += 1
json.dump(d, open(out, "w"), indent=1)
print("types", nt, "core taps", ntap, hashlib.sha256(open(out, "rb").read()).hexdigest()[:16])
