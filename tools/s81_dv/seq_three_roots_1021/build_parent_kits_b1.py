#!/usr/bin/env python3
"""seq (B) parents dsdv_seq_host_b1m / b1f (STW-S81c-COLLA2 2026-10-22): the r3c cluster spec with the soft landing
halves replaced by the two CLOSED hard band children (dsdv_sh_lb_lk / dsdv_sh_lb_vc, views of kits dsdv_sh_lb_*_b1m /
_b1f) at the planned positions of results/arch/seq_b1_bands_1022/review/plan_b1{m,f}.json.  Same module, ports,
outline 475.2 x 1339.2 and the three closed children unchanged; the parent keeps no soft register (wires only), so the
r3c soft-band fences / fence release are dropped; the lp record stays (same regions/clock ports; its landings now sit inside the bands)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
base = json.loads((ROOT / "physical/ref_tile/dsdv_seq_host_r3c/spec.json").read_text())
JOB = "dsdv_sh_lb_{b}_b1m-dsdv_sh_lb_{b}_b1m-a8b9dc305"
# MAIN b1m and FB b1f2 both use the MAIN band views (21.6-um seams; the FB band views' 10.8-um seams are retired, STEWARD
# 10-22): b1f2 = the alternate parent recipe (placement density 0.4 instead of 0.5: more parent routing room at the seams).
for v, pd in (("m", None), ("f2", 0.4)):
    plan = json.loads((ROOT / "results/arch/seq_b1_bands_1022/review/plan_b1m.json").read_text())
    at = {b[0].split()[0]: [round(b[1], 1), round(b[2], 1)] for b in plan["blocks"]}
    name = f"dsdv_seq_host_b1{v}"
    s = json.loads(json.dumps(base)); s["name"] = name
    s["sources"] = [x for x in s["sources"] if not x.endswith("dsdv_seq_host_c_r3_lp.sv")] + \
        ["rtl/dsrom_sys/s81_dv/unit/r3/dsdv_seq_host_c_r3_lb.sv"]
    for c in s["children"]:
        assert at[c["inst"]] == [round(x, 1) for x in c["at"]], (c, at)
    s["children"] += [
        {"view": "physical/ref_tile/dsdv_sh_lb_lk_b1m/views/dsdv_sh_lb_lk", "count": 1, "inst": "u_blk", "at": at["u_blk"], "orient": "R0"},
        {"view": "physical/ref_tile/dsdv_sh_lb_vc_b1m/views/dsdv_sh_lb_vc", "count": 1, "inst": "u_bvc", "at": at["u_bvc"], "orient": "R0"}]
    s["child_centre_tap"] = dict(s["child_centre_tap"], children=["u_l0", "u_l1", "u_l2", "u_blk", "u_bvc"])
    # STEWARD (A) 10-22: the bands own pins on two region roots each (lk+sq / sq+vc): declared, CLOSED records named
    s["multi_root_children"] = [{"inst": "u_blk", "job": JOB.format(b="lk")}, {"inst": "u_bvc", "job": JOB.format(b="vc")}]
    if pd is not None:
        s["route"] = dict(s["route"], pd=pd)
    for k in ("pin_hook_before_flops", "pre_dpl_extra"):
        s.pop(k, None)
    s["structural_change"] = ("seq (B) parent (successor of r3e/r3f: soft landing halves under one root per region strung along "
        "1,339-um faces, ck_lk spread 452/378): the landing halves + regional reset runs are hardened VERBATIM in the CLOSED band "
        "children dsdv_sh_lb_lk/vc_b1m (daemon a8b9dc305; declared multi_root_children); the parent = 3 closed children + 2 closed bands, wires only, "
        "every parent root feeds only hard-child clock pins.  Same module/ports/edges/outline.")
    s["job"] = dict(s["job"], owner="STW-S81c-COLLA2", branch="claude/s81-seq-b1-1022", tag=name,
        purpose=f"seq (B) parent ({'MAIN' if v == 'm' else 'FB: alternate parent recipe pd 0.4'}) on the closed MAIN band views",
        views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}")
    s["job"]["extra_paths"] = [p for p in s["job"].get("extra_paths", []) if (ROOT / p).exists()] + \
        ["physical/ref_tile/dsdv_sh_lb_lk_b1m/views", "physical/ref_tile/dsdv_sh_lb_vc_b1m/views"] + \
        [f"results/closure_loop/{JOB.format(b=b)}" for b in ("lk", "vc")] + [f"results/rtl/ref_tile/dsdv_sh_lb_{b}_b1m" for b in ("lk", "vc")]
    d = ROOT / "physical/ref_tile" / name; d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print(name, at["u_blk"], at["u_bvc"])
