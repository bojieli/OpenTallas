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
for v in "mf":
    plan = json.loads((ROOT / f"results/arch/seq_b1_bands_1022/review/plan_b1{v}.json").read_text())
    at = {b[0].split()[0]: [round(b[1], 1), round(b[2], 1)] for b in plan["blocks"]}
    name = f"dsdv_seq_host_b1{v}"
    s = json.loads(json.dumps(base)); s["name"] = name
    s["sources"] = [x for x in s["sources"] if not x.endswith("dsdv_seq_host_c_r3_lp.sv")] + \
        ["rtl/dsrom_sys/s81_dv/unit/r3/dsdv_seq_host_c_r3_lb.sv"]
    for c in s["children"]:
        assert at[c["inst"]] == [round(x, 1) for x in c["at"]], (c, at)
    s["children"] += [
        {"view": f"physical/ref_tile/dsdv_sh_lb_lk_b1{v}/views/dsdv_sh_lb_lk", "count": 1, "inst": "u_blk", "at": at["u_blk"], "orient": "R0"},
        {"view": f"physical/ref_tile/dsdv_sh_lb_vc_b1{v}/views/dsdv_sh_lb_vc", "count": 1, "inst": "u_bvc", "at": at["u_bvc"], "orient": "R0"}]
    s["child_centre_tap"] = dict(s["child_centre_tap"], children=["u_l0", "u_l1", "u_l2", "u_blk", "u_bvc"])
    for k in ("pin_hook_before_flops", "pre_dpl_extra"):
        s.pop(k, None)
    s["structural_change"] = ("seq (B) parent (successor of r3e/r3f: soft landing halves under one root per region strung along "
        "1,339-um faces, ck_lk spread 452/378): the landing halves + regional reset runs are hardened VERBATIM in the CLOSED band "
        "children dsdv_sh_lb_lk/vc_b1" + v + " (daemon a8b9dc305); the parent = 3 closed children + 2 closed bands, wires only, "
        "every parent root feeds only hard-child clock pins.  Same module/ports/edges/outline.")
    s["job"] = dict(s["job"], owner="STW-S81c-COLLA2", branch="claude/s81-seq-b1-1022", tag=name,
        purpose=f"seq (B) parent ({'MAIN' if v == 'm' else 'FB'}) on closed band views",
        views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}")
    s["job"]["extra_paths"] = [p for p in s["job"].get("extra_paths", []) if (ROOT / p).exists()] + \
        [f"physical/ref_tile/dsdv_sh_lb_lk_b1{v}/views", f"physical/ref_tile/dsdv_sh_lb_vc_b1{v}/views"]
    d = ROOT / "physical/ref_tile" / name; d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print(name, at["u_blk"], at["u_bvc"])
