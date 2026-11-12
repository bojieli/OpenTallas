"""VL2QC-CB private kit spec from an s25 wave spec (same src 4e2764d237, sidecar, gen_args, flow tag, edge_outline).
Overrides item, plan, bind_out, root/work, hosts (place off epyc9), gen_host epyc9 (src lives there). DO_NOT_COUNT.
usage: mkspec25.py BASE_SPEC ITEM PLAN BIND_OUT OUTDIR TAG"""
import json, sys, os, shutil
base, item, plan, bind_out, outdir, tag = sys.argv[1:7]
s = json.load(open(base))
W = "/srv/opentallas-scratch2/claude/vislayout2-qc"
for k in ("resume_from", "start_delay_s"):
    s.pop(k, None)
s.update(item=item, event="vl2qccb", plan=plan, root=f"{W}/cb/runs/{tag}", work=f"{W}/cb/runs/{tag}/items/{item}/attempt_1",
         gen_host="epyc9", hosts=["epyc2", "epyc7"], place_prefer=["epyc2", "epyc7"], hub="intel2", crit=False)
s["kit_rtl"] = dict(s["kit_rtl"], bind_out=bind_out, note="VL2QC-CB private (DO_NOT_COUNT)")
env = dict(s.get("gen_env") or {}); env["OT_GRT_TRANSITION_MODE"] = "edge_outline"; env["OT_FLOW_TAG"] = "flow-20261108-ef-qc"
s["gen_env"] = env
os.makedirs(outdir, exist_ok=True)
json.dump(s, open(os.path.join(outdir, "spec.json"), "w"), indent=1)
fl = os.path.join(os.path.dirname(base), "future_lec")
if os.path.isdir(fl) and not os.path.exists(os.path.join(outdir, "future_lec")):
    shutil.copytree(fl, os.path.join(outdir, "future_lec"))
print("spec", outdir, s["work"])
