#!/usr/bin/env python3
"""CLOCK-KV-R17: collect results/clock_kv_r17/summary.json from the run dir (sta/*/die_sta_related.json, mc*/die_*.json)."""
import json, sys, datetime
from pathlib import Path
R = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
def g(n):
    d = json.loads((R / "sta" / n / "die_sta_related.json").read_text())
    res = {}
    for k in ("intra", "seam"):
        t = d["corners"]["TT"]["classes"][k]; f = d["corners"]["FF"]["classes"][k]
        rt, rf = t.get("real_view", {}), f.get("real_view", {})
        res[k] = dict(all_tt_setup=t["worst_setup_slack_ps"], all_ff_hold=f["worst_hold_slack_ps"],
                      real_tt_setup=rt.get("worst_setup_slack_ps"), real_ff_hold=rf.get("worst_hold_slack_ps"),
                      real_ff_hold_neg=rf.get("hold_neg_pairs"), real_pairs=rf.get("pairs_with_real_endpoint"),
                      both_real_tt_setup=rt.get("both_real", {}).get("worst_setup_slack_ps"),
                      both_real_ff_hold=rf.get("both_real", {}).get("worst_hold_slack_ps"),
                      real_worst_hold=rf.get("worst_hold"),
                      kit_contract_ff=f.get("kit_contract_hold", {}).get("worst_hold_bound_ps"))
    res["mesh_unc_max_ps"] = {c: d["corners"][c].get("mesh_signoff", {}).get("unc_max_ps") for c in ("TT", "FF")}
    res["droop_region"] = d["corners"]["FF"].get("clock_ocv", {}).get("droop_region")
    return res
runs = sorted(p.name for p in (R / "sta").iterdir() if (p / "die_sta_related.json").exists())
S = dict(lane="CLOCK-KV-R17", date=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
         status="own scripts; numbers UNCHECKED-independent (NUMBER-CHECK owed)",
         mesh_signoff={m: {c: json.loads((R / m / f"die_{c}.json").read_text())["summary"] for c in ("TT", "FF")}
                       for m in ("mc", "mc14")},
         sta={n: g(n) for n in runs})
(out / "summary_raw.json").write_text(json.dumps(S, indent=1) + "\n")
print(json.dumps({n: {k: (v["real_tt_setup"], v["real_ff_hold"], v["both_real_ff_hold"]) for k, v in S["sta"][n].items() if k in ("intra", "seam")} for n in runs}, indent=0))
