"""KV real example: count_align_bind.strap_ties on the DIE-KV-5 partition-frame bind (H200B spice, --parts ocv) + plan
hm_r26q9c; table = the bind's own crossings (src/dst region + partition)."""
import json, sys
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import count_align_bind as CAB
D = sys.argv[2]
b = json.load(open(D + "/kv_h200b_spice_bind_parts.json")); plan = json.load(open(D + "/hm_r26q9c.json"))
table = dict(ports=[dict(port=pid, src_region=c["src"], dst_region=c["dst"], src=c["src_part"], dst=c["dst_part"])
                    for pid, c in b["ports"].items()])
t = CAB.annotate_table(table, b, strap_form=True)
st = CAB.strap_ties(t["count_aligned"], plan)
json.dump(st, open(D + "/kv_strap_ties.json", "w"), indent=1)
print(json.dumps(st["summary"]))
rs = {tn: v["residual_split"] for tn, v in st["types"].items() if v.get("residual_split")}
print("residual_split", json.dumps(rs)[:600])
old = json.load(open(D + "/strap_kits_parts_spice.json"))
print("DIE-KV-5 list summary", json.dumps(old.get("summary", {k: old[k] for k in list(old)[:6] if not isinstance(old[k], dict)}))[:600])
