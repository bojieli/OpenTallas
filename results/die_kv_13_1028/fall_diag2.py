# DIE-KV-13 INFO diag: fg1 (FLOW-GEN-1 6672c5921) phase plan on the measured-fall proof -> which crossings FAIL and why
import json, sys, copy, collections
sys.path.insert(0, sys.argv[1])
import count_align_bind as CB
R = "/srv/opentallas-scratch2/claude/die-kv-13-1028"; P = sys.argv[2]; PL = "/srv/opentallas-scratch2/claude/die-kv-4-1027/pd9c/hm_r26q9c.json"
argv = [R + "/ca_inv_r150/inv_r150_spice_xing_lpo.json", "--from-ocv", "--parts", "ocv", "--sta-proof", P, "--sta-plan", PL,
        "--sta-clock-cal", "spice", "--sta-cppr-lca", "--sta-clock-ocv", "table", "--sta-clock-droop", "shared",
        "--sta-droop-regions", P + "/droop_regions.json", "--sta-core-latency-ff", "202.5", "--start-tree", "clock",
        "--start-clean", "phase", "--samples", "50", "--out", "/dev/null"]
cap = {}
def bind(plan, *a, **k):
    cap["plan"] = plan; raise SystemExit(0)
CB.bind = bind
try: CB.main(argv)
except SystemExit: pass
p = cap["plan"]; rows = p["crossings"]
bad = [r for r in rows if r.get("depth") is None or r.get("rtl") is None]
print("summary", json.dumps({k: v for k, v in p["summary"].items() if not isinstance(v, (dict, list))})[:1500])
print("bad", len(bad), collections.Counter(r.get("kind") for r in bad), collections.Counter(r.get("fail") or r.get("reason") or r.get("status") for r in bad).most_common(5))
regs = p["regions"]; ef = {k for k, v in (regs.items() if isinstance(regs, dict) else []) if v.get("edge_fall")}
print("edge_fall regions", len(ef), "bad dst in edge_fall regions", sum(1 for r in bad if r.get("dst") in ef or r.get("dst_region") in ef))
print(json.dumps(bad[0])[:1200])
