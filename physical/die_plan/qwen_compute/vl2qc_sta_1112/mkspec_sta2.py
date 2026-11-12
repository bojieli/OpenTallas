"""VL2QC-STA private kit spec for a type with or without its own s25 wave spec.
REF = an s25 wave spec (the type's own, or a same-family sibling's); OWN = the type's latest wave spec (any plan) for the
type-specific gen_args (sidecar path re-pointed to the s25 src). Private plan plan_vl2_sta_a, private bind sta/bind_a,
gen epyc9 (s25 src lives there), place epyc7/epyc8/intel1 (not epyc9, not epyc2), edge_outline + flow tag; the
LAND-RING-2 OT_CLAND_STRIP_DENS item env is dropped (this arm is SRAM positions only). DO_NOT_COUNT.
usage: mkspec_sta2.py REF_S25_SPEC OWN_SPEC ITEM OUTDIR"""
import json, sys, os, shutil
ref, own, item, outdir = sys.argv[1:5]
s = json.load(open(ref)); o = json.load(open(own))
assert "plan_qc99_s25" in s["plan"], s["plan"]
assert o["item"] == item, (o["item"], item)
SRC = "/srv/opentallas-scratch2/claude/kw45/src_qc_s25_4e2764d237"
assert s["src"] == SRC, s["src"]
W = "/srv/opentallas-scratch2/claude/vislayout2-qc"
ga = list(o["gen_args"])
for i, a in enumerate(ga):
    if a.endswith("qc_start_1106/runtime/sidecar_pv.json"):
        ga[i] = f"{SRC}/physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar_pv.json"
for k in ("resume_from", "region_guide_geom"):
    s.pop(k, None)
for k in ("geom_waivers", "cland_pinslot", "relay_bay_re", "preflight_args", "core_kit", "kind"):
    if k in o:
        s[k] = o[k]
s.update(item=item, gen_args=ga, event="vl2qcsta", plan=f"{W}/sta/por/plan_vl2_sta_a.json", root=f"{W}/sta/runs/a",
         work=f"{W}/sta/runs/a/items/{item}/attempt_1", gen_host="epyc9", hosts=["epyc7", "epyc8", "intel1"],
         place_prefer=["epyc8", "epyc7", "intel1"], hub="intel2", crit=False,
         queue_src="claude/qc-event-s25-1111@4e2764d237d8 + VL2QC-STA private plan plan_vl2_sta_a")
s["kit_rtl"] = dict(s["kit_rtl"]); s["kit_rtl"]["bind_out"] = f"{W}/sta/bind_a"
s["kit_rtl"]["note"] = "VL2QC-STA: private strict bind of plan_vl2_sta_a on src_qc_s25_4e2764d237"
env = {k: v for k, v in (s.get("gen_env") or {}).items() if k != "OT_CLAND_STRIP_DENS"}
env["OT_GRT_TRANSITION_MODE"] = "edge_outline"; env.setdefault("OT_FLOW_TAG", "flow-20261108-ef-qc")
s["gen_env"] = env
os.makedirs(outdir, exist_ok=True)
json.dump(s, open(os.path.join(outdir, "spec.json"), "w"), indent=1)
fl = os.path.join(os.path.dirname(ref), "future_lec")
if os.path.isdir(fl) and not os.path.exists(os.path.join(outdir, "future_lec")):
    shutil.copytree(fl, os.path.join(outdir, "future_lec"))
print("spec", item, s["work"], ga[-4:])
