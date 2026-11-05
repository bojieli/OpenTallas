#!/usr/bin/env python3
"""HBM-REFORM-B4 d44v part 25 pre: slot ot_hbm_svc_wb_kport_q 475.2x475.2 -> 527.04x544.32; u_wbk_Q__q1 origin y -8.64 (gaps there: E 17.28, N 8.64, S 21.6), q0 origin kept.
Root synth 57k cells 7511 um2 + 8 macros and sw 160k cells 19982 um2 do not fit the old slot; stdcell util by core area about 0.47 root, 0.48 sw [ESTIMATE]."""
import json, sys
from pathlib import Path
pd = Path(sys.argv[1]); D = json.loads((pd / "die_plan.json").read_text()); n = 0
for ty in D["partition_types"].values():
    for h in ty.get("hard_cores") or []:
        if h["module"] == "ot_hbm_svc_wb_kport_q":
            assert h["outline_um"] == [475.2, 475.2]; h["outline_um"] = [527.04, 544.32]; n += 1
            if h["inst"] == "u_wbk_Q__q1": h["origin_um"] = [h["origin_um"][0], round(h["origin_um"][1] - 8.64, 3)]
(pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n"); print("part 25 pre rows", n)
