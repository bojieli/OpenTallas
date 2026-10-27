#!/usr/bin/env python3
"""HEAD-CORE-R18: write the per-view hold allowance JSON for elemA m2/m12 (COORD RULING HEAD-CORE-R17 (2)).
  mk_allowance.py VIEW WS_FLOOR_PS GATE_WS_PS GATE_N   (R18: m2 -100 -76.523 2165, m12 -100 -88.909 2181)  -> hold_allowance/elemA_<VIEW>.json
Values: insertion from elemA_insertion_rcx.json (meas_ck.tcl on routed 6_final.odb + 6_final.spef, corner FF);
constraint.sdc sha256 of the R16 kit (identical for m2/m12); gate ws/n = the ECO's RCX-view gate stop."""
import json, sys
from pathlib import Path
H = Path(__file__).resolve().parent
view, floor, gws, gn = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
ins = json.loads((H / "elemA_insertion_rcx.json").read_text())[f"{view}_FF"]
a = dict(
    schema="ot_hold_allowance/1", id=f"HEAD-R18-elemA_{view}-ffhold",
    ruling="COORD 2026-10-27 07:47 PDT HEAD-CORE-R17 rulings (2): option (a) accepted, not structural "
           "(boundary contract -40 + centre-entry tree +25 ps); ~3 HB4 at the input registers = owner-allowed data hold "
           "buffers (METHODOLOGY 12.4a a1), ledgered; conditions FF insertion inside 202.5+-20, no change to the die IO "
           "contract or vclk binding",
    ledger="~/coord/lanes/HEAD-CORE-LAT.md HEAD-CORE-R18 RESULT line + results/s81_head_r18/README.md",
    design_nickname="hd_elemA_rb", kit_dir=f"elemA_{view}", stage="post_route_eco",
    cause=f"RCX-view FF hold ws {gws:.2f} ps / {gn} endpoints at the post-route ECO gate (GRT {'-102.82/795' if view == 'm2' else '-102.96/810'}); "
          "input port -> register paths under the die IO min input delay -40 ps",
    limits=dict(ws_floor_ps=floor, max_endpoints=2200, classes=["I2R"]),
    cap_reason=f"RCX view (routed 6_final.spef) has ws {gws:.2f} ps INSIDE the default -100 floor but {gn} failing endpoints "
               "> 2000 (GRT basis 795/810); same input-register cause; cap 2200 = measured + <2 %; classes I2R only; PENDING COORD confirmation",
    binding=dict(ot_vclk_tt=250, ot_vclk_ff=202.5,
                 constraint_sdc_sha256="38780311a07318a63695c25066643f18e49fbcce3cb31516a80a817b63f1345f"),
    insertion=dict(corner="FF", statistic="mean", band_ps=[182.5, 222.5], tsv=ins["tsv"], tsv_sha256=ins["sha256"],
                   basis=ins["basis"], mean_ps=ins["mean"], min_ps=ins["min"], max_ps=ins["max"], n=ins["n"]),
    expected="HB4xp67 only (hold_pad_hb4.tcl), on input-register data paths; clock untouched")
(H / "hold_allowance").mkdir(exist_ok=True)
(H / "hold_allowance" / f"elemA_{view}.json").write_text(json.dumps(a, indent=1) + "\n")
print(H / "hold_allowance" / f"elemA_{view}.json")
