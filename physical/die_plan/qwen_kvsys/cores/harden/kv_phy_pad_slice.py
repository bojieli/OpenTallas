#!/usr/bin/env python3
"""KV-KITS-9 10-28: KV core slice for qkd_hr_phy_pad (COORD 07:12: regenerate phy_pad with a KV core slice and the
planned 12.3 core latency 250 TT / 202.5 FF; no more hold buffers).

Root cause of 8e9cd27f9e35 (CTS RSZ-0060 after 4120 hold buffers, out_d hold -73 ps): the q9 kit had no planned core
latency, so stock CTS built a ~160 ps tree while the kit io frame (vclk source latency 250, set_output_delay -min 0)
assumes the 12.3 common latency: every out_d pin flop launched ~90 ps early against the die frame.

Plan-only slice (no measurement input), METHODOLOGY 12.8a/12.8c (kv_core_slice.py rules):
  entry  12.8a centre entry island 8.64 x 8.64 on the 4.32 PG lattice around the q9 clock pin ck (43.224, 47.52) M5;
  trunk  12.8c designed fixed trunk for a shallow core: N x BUFx4 from the KV-CORE-SLICE-1 insertion model
         (TT = A + B x L_max, A 86.86 / B 0.8057 / FF_RATIO 0.8118, rms 4.8 ps; slice24 kv_core_slice.json),
         N = round((250 - pred) / 23.9 ps BUFx4 stage), placed FIRM in the entry island;
  leaf   one CTS-open leaf below the trunk with every clock sink of the kit's own synthesis netlist (census).
usage: phy_pad_slice.py KIT_DIR PLAN_JSON OUT_DIR [--trunk N]
  --trunk N (KV-KITS-15, opt-in): fixed trunk stage count from a MEASURED re-prediction instead of the slice24 model
            (DIE-KV-13 results/die_kv_13_1028/core_seam_hold/phy_pad_trunk_repredict.json: the A+B*L model
            over-predicts this core's tree ~60 ps TT; 7 stages is the only count inside the 12.3 band). Default: model.
"""
import hashlib
import json
import math
import re
import sys
from pathlib import Path

A, B, FF_RATIO, RMS = 86.86, 0.8057, 0.8118, 4.8      # slice24 kv_core_slice.json "model" (KV-CORE-SLICE-1)
STAGE = dict(TT=23.9, FF=17.6)                         # BUFx4_ASAP7_75t_R steady chain (kv_core_slice.BUF_STAGE_PS)
TARGET = dict(TT=250.0, FF=202.5)
ISL = 8.64
LAT = 4.32


def main(kit, plan, out, trunk=None):
    kit, out = Path(kit), Path(out)
    fz = json.loads((kit / "freeze.json").read_text())
    w, h = fz["outline_um"]
    pins = json.loads((kit / "pins.json").read_text())
    ck = [p for p in pins if p.get("clock")]
    assert len(ck) == 1 and ck[0]["bus"] == "ck" and ck[0]["face"] == "interior", ck
    cx, cy = ck[0]["x"], ck[0]["y"]
    # entry island: 8.64 square centred on the lattice point nearest the pin
    gx, gy = round(cx / LAT) * LAT, round(cy / LAT) * LAT
    isl = [round(gx - ISL / 2, 3), round(gy - ISL / 2, 3), round(gx + ISL / 2, 3), round(gy + ISL / 2, 3)]
    assert isl[0] <= cx <= isl[2] and isl[1] <= cy <= isl[3]
    # census: every flop clock pin of the kit's own synthesis netlist (no macros in this core)
    v = (kit / "1_synth_odb.v").read_text()
    cells = re.findall(r"^\s*(DFF\w+|DHL\w+|DLL\w+|SDF\w+|ICG\w+)\s+(\\\S+|\S+)\s*\(", v, re.M)
    assert not [c for c, _ in cells if c.startswith("ICG")], "clock gates present: not a single-leaf core"
    sinks = []
    for _, n in cells:
        n = n[1:] if n.startswith("\\") else n
        sinks.append(n.replace("[", "\\[").replace("]", "\\]") + "/CLK")
    assert len(sinks) == len(set(sinks)) and sinks
    # 12.8c trunk from the plan insertion model
    lmax = max(abs(cx - x) + abs(cy - y) for x in (0, w) for y in (0, h))
    pred = A + B * lmax
    n = max(0, round((TARGET["TT"] - pred) / STAGE["TT"])) if trunk is None else int(trunk)
    tt = pred + n * STAGE["TT"]
    ff = FF_RATIO * pred + n * STAGE["FF"]
    # Trunk sites (pv_pair core_tree convention: node xy on the 2.16 sub-lattice of the entry island).  Node x kept at
    # 1.08 / 3.24 mod 4.32, clear of the M5 PG strap pair (pdn.tcl: width 0.12, spacing 0.072, pitch 4.32, offset 2.064
    # -> both nets inside the conservative band 1.9..2.6 mod 4.32 declared below), so every edge has a legal L.
    pos = [(gx - 1.08, gy - 2.16), (gx + 1.08, gy - 2.16), (gx + 1.08, gy + 2.16), (gx - 1.08, gy + 2.16)]
    # KV-KITS-15 --trunk > 4: the outer x = +-3.24 columns of the same rows (same 1.08/3.24 mod 4.32 PG clearance)
    pos += [(gx - 3.24, gy + 2.16), (gx - 3.24, gy - 2.16), (gx + 3.24, gy - 2.16), (gx + 3.24, gy + 2.16)]
    assert n <= len(pos), n
    nodes, par = [], "port:ck[0]"
    for i in range(n):
        x, y = (round(v, 3) for v in pos[i])
        nodes.append(dict(name=f"mp_pad_ck_tr{i}", master="BUFx4_ASAP7_75t_R", xy_um=[x, y], island_rect_um=isl,
                          parent=par))
        par = nodes[-1]["name"]
    ca = [float(v) for v in re.search(r"CORE_AREA\s*=\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
                                      (kit / "config.mk").read_text()).groups()]
    m5 = [[round(LAT * k + 1.9, 3), ca[1], round(LAT * k + 2.6, 3), ca[3]] for k in range(int(w / LAT) + 1)
          if LAT * k + 2.6 <= w]
    plan_sha = hashlib.sha256(Path(plan).read_bytes()).hexdigest()
    sl = {
        "schema": "opentallas.master_plan_slice.v1", "die": "qwen_kvsys", "kind": "core",
        "type": fz["type"], "module": fz["module"], "instances": [fz.get("plan_inst")],
        "plan": str(plan), "plan_sha256": plan_sha,
        "master_plan_sha256": f"hm_r26q9 (KV slice, KV-KITS-9 phy_pad trunk; no frozen KV master plan)",
        "frozen": False, "outline_um": [w, h], "keepouts": [], "bays": [], "entry_pins": [], "hard_cores": [],
        "corridors": [], "gates": {},
        "islands": [{"name": "pad_ck_entry", "rect_um": isl, "centre_um": [gx, gy], "use": "clock_driver",
                     "via_stack": ["M9", "M5"], "clock_pin": {"layer": "M5", "xy_um": [cx, cy]},
                     "note": "12.8a centre entry = the q9 plan ck pin (unchanged)"}],
        "latency": {"common_clock_latency_ps": TARGET, "tol_ps": 20, "early_taps": False},
        "core_clock_port": "ck[0]",
        "pg_obstructions_um": {"M5": m5, "M4": [],
                               "note": "M5 = conservative band 1.9..2.6 mod 4.32 around the kit pdn.tcl strap pair (both nets, "
                                       "either offset origin); M4 [] as the GEOM-passed pv_pair slice"},
        "pushdown": {"islands": []},
        "core_tree": {
            "clock_port": "ck[0]",   # netlist BTerm = the bus bit (pv_pair s1__clk[0] form; place 4185915 stopped on OT_CORE_INFRA_CLOCK_ENTRY_PORT ck)
            "form": f"entry -> {n} x BUFx4 fixed trunk (12.8c, FIRM in the entry island) -> one CTS-open leaf",
            "trunk_layers": ["M4", "M5"],
            "nodes": nodes,
            "leaves": [{"node": par, "cts_open": True, "domain_sinks": len(sinks), "cts_fanout": 24,
                        "load_class": "register", "sinks": sinks}],
            "insertion_model": {"basis": "KV-CORE-SLICE-1 slice24 model TT = A + B x L_max (rms 4.8, loo_max 10.9)",
                                "A": A, "B": B, "FF_RATIO": FF_RATIO, "L_max_um": lmax, "pred_tree_TT_ps": round(pred, 2),
                                "trunk_stages": n, "stage_ps": STAGE, "pred_TT_ps": round(tt, 2),
                                "pred_FF_ps": round(ff, 2), "label": "UNCHECKED until the routed kit reports it",
                                **({"trunk_override": {"stages": n, "basis": "DIE-KV-13 phy_pad_trunk_repredict.json (KV-KITS-13 probe, measured 4-stage insertion TT 180.1-198.3 / FF 136.5-149.8 + n x stage)", "pred_TT_ps": [round(180.1 + (n - 4) * STAGE["TT"], 1), round(198.3 + (n - 4) * STAGE["TT"], 1)], "pred_FF_ps": [round(136.5 + (n - 4) * STAGE["FF"], 1), round(149.8 + (n - 4) * STAGE["FF"], 1)]}} if trunk is not None else {})},
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{fz['module']}.json").write_text(json.dumps(sl, indent=1) + "\n")
    print(json.dumps(dict(module=fz["module"], sinks=len(sinks), L_max=lmax, pred_tree=round(pred, 2), trunk=n,
                          pred_TT=round(tt, 2), pred_FF=round(ff, 2), island=isl)))


if __name__ == "__main__":
    av = sys.argv[1:]
    tr = None
    if "--trunk" in av:
        i = av.index("--trunk"); tr = int(av[i + 1]); del av[i:i + 2]
    main(*av[:3], trunk=tr)
