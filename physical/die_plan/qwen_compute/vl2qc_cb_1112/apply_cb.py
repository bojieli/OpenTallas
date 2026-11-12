"""VL2QC-CB: apply delta_cb_qc4 ({type:{tile:[x,y,orient]}}) to a base plan (positions/orients only).
usage: apply_cb.py BASE OUT DELTA_OUT [types-comma|all]"""
import json, sys, hashlib
src, dst, dout = sys.argv[1:4]
only = None if len(sys.argv) < 5 or sys.argv[4] == "all" else set(sys.argv[4].split(","))
raw = open(src, "rb").read(); p = json.loads(raw)
d = json.load(open("/srv/opentallas-scratch2/claude/vislayout2-qc/delta_cb_qc4.json"))
ed = []
for tn, tiles in d.items():
    if only and tn not in only: continue
    hcs = {c["inst"].split(".")[-1]: c for c in p["partition_types"][tn]["hard_cores"]}
    for k, (x, y, o) in tiles.items():
        h = hcs[k]
        if h["origin_um"] != [x, y] or h["orient"] != o:
            ed.append(dict(type=tn, inst=h["inst"], was=dict(origin_um=h["origin_um"], orient=h["orient"]), now=dict(origin_um=[x, y], orient=o)))
            h["origin_um"] = [x, y]; h["orient"] = o
p["note"] = p.get("note", "") + " | vl2qc_cb (VL2QC-CB 11-12): round-1 delta_cb_qc4 on s25"
out = json.dumps(p, indent=1); open(dst, "w").write(out)
json.dump(dict(base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=hashlib.sha256(out.encode()).hexdigest(), edits=ed), open(dout, "w"), indent=1)
print("edits", len(ed), "sha", hashlib.sha256(out.encode()).hexdigest()[:12])
for e in ed: print(" ", e["type"], e["inst"].split(".")[-1], e["was"], "->", e["now"])
