#!/usr/bin/env python3
"""el1013-idx-tiles: per-leaf generic-synthesis census (yosys synth -flatten, no technology mapping): flop count, flops
on a reset net, and the largest non-clock fanout BEFORE buffering (cell-input loads a net bit).  Planning evidence for
SPEC gate (e), not a route result.  usage: census.py ROOT YOSYS OUTDIR"""
import json, subprocess, sys, collections
from pathlib import Path
root, yosys, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
D = root / "rtl/hbm_accel/generic/idx"; res = {}
for top in ["ot_hgi_idxw_lane", "ot_hgi_idxw_qcore", "ot_hgi_idxw_keep", "ot_hgi_idxw_beat", "ot_hgi_idxw_wr"]:
    js = out / f"{top}.json"
    r = subprocess.run([yosys, "-q", "-p", f"read_verilog -sv -DSYNTHESIS {D / (top + '.sv')}; synth -top {top} -flatten; "
                        f"check; write_json {js}"], capture_output=True, text=True)
    if r.returncode != 0: res[top] = {"error": (r.stdout + r.stderr)[-400:]}; continue
    m = json.load(open(js))["modules"][top]; js.unlink()
    names = {}
    for n, v in m["netnames"].items():
        for i, b in enumerate(v["bits"]):
            if isinstance(b, int) and (b not in names or not v.get("hide_name")): names[b] = f"{n}[{i}]"
    fan = collections.Counter(); ff = 0; clk = set(); rst = collections.Counter()
    for c in m["cells"].values():
        isff = "DFF" in c["type"] or "dff" in c["type"]
        ff += isff
        for port, bits in c["connections"].items():
            if c["port_directions"].get(port) != "input": continue
            for b in bits:
                if not isinstance(b, int): continue
                if isff and port == "C": clk.add(b); continue
                fan[b] += 1
                if isff and port in ("R", "S", "ARST", "SRST"): rst[b] += 1
    top5 = [(names.get(b, str(b)), n) for b, n in fan.most_common() if b not in clk][:6]
    res[top] = {"flops": ff, "cells": len(m["cells"]), "max_nonclock_fanout": top5[0][1], "top_fanout_nets": top5,
                "reset_pin_loads_max": max(rst.values()) if rst else 0, "check": "problems" not in r.stdout or "0 problems" in r.stdout}
    print(top, json.dumps(res[top]), flush=True)
json.dump(res, open(out / "census.json", "w"), indent=1)
