#!/usr/bin/env python3
"""KV-IOCOR-1 11-06: kv3_io_cor + kv3_io_cor_v1, RE-FORM after >=2 GRT-0116 attempts (io_cor attempt_2 433,700 overflow;
io_cor_v1 attempt_7), same classes as kv3_io_ft (ftwreg_1104 + ioft ring_place ff, signed LOCAL_PASS_NEEDS_PARENT).
(1) GRT congestion: 100% of overflow inside the plain-tag wide rings (all ring cells FIRM in netlist order, local ring
    nets median HPWL 44-54 um vs 1.6 um in the +x+ff i_host_fdi band).  ring_place ff on every wide band (flops FIRM
    bit-major, ring logic to GPL); S-face strips fill_axis x (rows=2; the +ff 'band as +x' rows=1 strip left 1.0-1.6k
    overflow in io_cor ft15_i).  Kit proof: io_cor_vC + io_cor_v1_vA/vB GRT 0 overflow.
(2) GRT G2 setup_tt (io_cor_v1_vA -81.89): cland_fstart_in -> ring write-enable broadcast (BUFx24 fanout 152) carrying
    GRT hold pads (+132 ps), and ctl_w -> lap_ok/rv on the small rings (-34 at CTS).  Writer form WREG-1 on all rings
    (clock.landing_ring_wreg, strap K + 1 by bind, 0 data cycles) + private status bank (landing_control_status_copy).
No outline, pin or rect change.  Idempotent.  usage (repo root): event.py PLAN_IN PLAN_OUT"""
import json, sys
FF = {"kv3_io_cor": {"ft4_i": None, "ft5_i": None, "ft15_i": "x", "ft17_i": "x", "ft19_i": None},
      "kv3_io_cor_v1": {"ft7_i": None, "ft8_i": None, "ft11_i": None, "ft13_i": None, "ft23_i": None}}
a, b = sys.argv[1:3]
p = json.load(open(a))
for tn, wide in FF.items():
    t = p["partition_types"][tn]
    bands = t["clock"]["landing_contract"]["bands"]
    for bus, axis in wide.items():
        bands[bus]["ring_place"] = "ff"
        if axis: bands[bus]["fill_axis"] = axis
    rings = sorted(k for k, v in bands.items() if not k.startswith("monitor_") and v.get("rect_um"))
    t["clock"]["landing_ring_wreg"] = {"buses": rings, "dsrep": 1}
    t["landing_control_status_copy"] = True
json.dump(p, open(b, "w"), indent=1); open(b, "a").write("\n")
