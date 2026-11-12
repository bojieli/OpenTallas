"""VL2QC-STA private kit spec (kit_wave.py run-item) from the type's own s25 wave spec: private plan (plan_vl2_sta_a),
private strict bind (sta/bind_a), private root/work, gen on epyc9 (where the s25 src lives), place OFF epyc9 (COORD
11-12: hosts epyc7/epyc2), edge_outline GRT mode + flow tag kept from the wave spec. DO_NOT_COUNT.
usage: mkspec_sta.py WAVE_SPEC.json ITEM OUTDIR"""
import json, sys, os, shutil
base, item, outdir = sys.argv[1:4]
s = json.load(open(base))
assert s["item"] == item and "plan_qc99_s25" in s["plan"], (s["item"], s["plan"])
W = "/srv/opentallas-scratch2/claude/vislayout2-qc"
for k in ("resume_from", "region_guide_geom"):
    s.pop(k, None)
s.update(event="vl2qcsta", plan=f"{W}/sta/por/plan_vl2_sta_a.json", root=f"{W}/sta/runs/a",
         work=f"{W}/sta/runs/a/items/{item}/attempt_1", gen_host="epyc9", hosts=["epyc7", "epyc2"],
         place_prefer=["epyc7", "epyc2"], hub="intel2", crit=False,
         queue_src=s.get("queue_src", "") + " + VL2QC-STA private plan plan_vl2_sta_a")
s["kit_rtl"] = dict(s["kit_rtl"]); s["kit_rtl"]["bind_out"] = f"{W}/sta/bind_a"
s["kit_rtl"]["note"] = "VL2QC-STA: private strict bind of plan_vl2_sta_a on src_qc_s25_4e2764d237"
env = dict(s.get("gen_env") or {}); env["OT_GRT_TRANSITION_MODE"] = "edge_outline"; env.setdefault("OT_FLOW_TAG", "flow-20261108-ef-qc")
s["gen_env"] = env
os.makedirs(outdir, exist_ok=True)
json.dump(s, open(os.path.join(outdir, "spec.json"), "w"), indent=1)
fl = os.path.join(os.path.dirname(base), "future_lec")
if os.path.isdir(fl) and not os.path.exists(os.path.join(outdir, "future_lec")):
    shutil.copytree(fl, os.path.join(outdir, "future_lec"))
print("spec", outdir, s["work"])
