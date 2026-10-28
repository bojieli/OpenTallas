import json, sys, collections, subprocess
sys.path.insert(0, sys.argv[1])
import schema as S, gen_phys as G
def early(plan_path=None, raw=None):
    raw = raw or json.load(open(plan_path))
    P = S.Plan(raw)
    cnt = collections.Counter(p["type"] for p in P.parts.values())
    res = collections.defaultdict(lambda: dict(inst=0, early_inst=0, early_taps=0, pins=set(), max_ins_ff=0.0))
    for tn, t in P.types.items():
        hc = {h["inst"]: h for h in t.get("hard_cores", []) or []}
        for h in hc.values():
            res[h["module"]]["inst"] += cnt[tn]; res[h["module"]]["pins"].add(h.get("pins_file"))
        if (t.get("clock", {}) or {}).get("core_taps") != "early":
            continue
        try:
            rows = G.core_tap_rows(P, tn, "TT", pending=[]); rff = G.core_tap_rows(P, tn, "FF", pending=[])
        except Exception as e:
            print("ERR", tn, e, file=sys.stderr); continue
        seen_inst = set()
        for (pn, inst, pin, e, i), (_, _, _, e2, i2) in zip(rows, rff):
            m = hc[inst]["module"]
            res[m]["early_taps"] += cnt[tn]
            res[m]["max_ins_ff"] = max(res[m]["max_ins_ff"], i2)
            if inst not in seen_inst:
                seen_inst.add(inst); res[m]["early_inst"] += cnt[tn]
    return {k: dict(v, pins=sorted(x for x in v["pins"] if x)) for k, v in res.items()}
if __name__ == "__main__":
    out = {}
    for die, path in [a.split("=", 1) for a in sys.argv[2:]]:
        out[die] = early(path)
        e = {k: v for k, v in out[die].items() if v["early_taps"]}
        print(die, "modules", len(out[die]), "early-tapped modules", len(e), "early taps", sum(v["early_taps"] for v in e.values()))
    json.dump(out, open(sys.argv[0].replace("early.py", "early_out.json"), "w"), indent=1)
