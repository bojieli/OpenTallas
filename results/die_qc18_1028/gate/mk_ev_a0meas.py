# DIE-QC-18: trial12 event (DIE-QC-16 ev/qc_k2b_p12_a0early.json) with the 64 c_* A0 core taps set to the MEASURED
# routed A0 trunk insertion (median register/child-pin arrival, child 250/202.5): nk t5 665.8/576.5, nl b5 692.6/601.9.
import json, sys
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src)); T = d["partition_types"]
INS = {"qfd_tile_nk_a0c": (665.8, 576.5, "nk t5 DIE-QC-18 routed+OCV 62.3/62.0, median arrival (TT 648.0-681.3, FF 558.4-593.1)"),
       "qfd_tile_nl_a0c": (692.6, 601.9, "nl b5 DIE-QC-18 routed+OCV 60.8/58.9, median arrival (TT 679.5-711.1, FF 589.1-621.7)")}
n = 0
for tn, t in T.items():
    if not tn.startswith("cb"):
        continue
    mods = {h["inst"]: h["module"] for h in t["hard_cores"]}
    for tp in t["clock"]["taps"]:
        if tp.get("kind") != "core":
            continue
        a, b, w = INS[mods[tp["name"].split(".")[0]]]
        tp["insertion_ps"], tp["insertion_ff_ps"] = a, b
        tp["budget_owner"] = "DIE-QC-18 measured routed A0 trunk insertion (" + w + "; COORD 14:xx ruling: carry measured trunks into the die gate)"
        n += 1
json.dump(d, open(out, "w"), indent=1)
print("taps", n)
