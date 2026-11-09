"""KV-PLAN-1 11-09: vport W request pads for bind5 depths = the b2 table bind5 lands (results/die_kv_15_1028/vport_w_pads_b2.json)
+ the residual the boot generator measures ON bind5 (kv_boot_v36 path functions, pvages.py: DQ 16 on EN_3, ES_3, WN_3).
Same rule as physical/die_plan/qwen_kvsys/r8/vport_w_pads.py (pad = DQ - 15 on pr_t AND pr_valid), applied on top of b2
because bind5 already contains b2's pads (running vport_w_pads.py on bind5 against the base R8 would drop them).
  mk_wpads.py B2.json RESID.json OUT.json      RESID = {"vport_EN_3": 1, ...}"""
import sys, json, copy
b2, resid, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
t = copy.deepcopy(b2)
done = {}
for m in t["members"]:
    p = resid.get(m["sink"], 0)
    if p and m["sink_port"] in ("pr_t", "pr_valid"):
        m["pad"] += p
        m["landed"] += p
        m["w_pad"] = m.get("w_pad", 0) + p
        done.setdefault(m["sink"], []).append(m["sink_port"])
for vp, p in resid.items():
    if sorted(done.get(vp, [])) != ["pr_t", "pr_valid"]:
        raise SystemExit(f"{vp}: b2 has no aligned pr_t + pr_valid members to raise ({done.get(vp)})")
    t["ports"][vp]["pad"] += p
    t["ports"][vp]["W_padded"] += p
    t["ports"][vp]["DQ_bind5_residual"] = 15 + p
t["note"] = b2["note"] + f" | KV-PLAN-1 11-09: + bind5 residual {resid} (boot generator on dkv95/bind5)"
t["source_bind"] = "/srv/opentallas-scratch2/claude/dkv95/bind5 (on top of " + b2["source_bind"] + ")"
t["summary"]["pad_stages"] += sum(resid.values())
t["summary"]["pad_flops"] += sum(15 * p for p in resid.values())
open(out, "w").write(json.dumps(t, indent=1) + "\n")
print(json.dumps({vp: [(m["sink_port"], m["pad"], m["landed"]) for m in t["members"] if m["sink"] == vp] for vp in resid}))
