#!/usr/bin/env python3
"""HBM-COLLFUSE2-VME (10-20): compose the VMEARLY early-issue schedule (tools/hgi_sim/d4g_vmearly_1019.py, the lead model)
INTO the measured census (tools/hgi_sim/toksim_hbm_census_1019.py --measured): T.schedule = census(measured costs) on top
of the vmearly schedule (early VM issue per client, OT_VME_N), so every measured record keeps its measured cost and the
hideable VM-bank round trip of each client is exposed only as the early-issue rule leaves it.  OT_VME_BLDMA=all keeps the
release row's every-DMA-record bl_dma charge (only the early issue changes).  OT_VME_N=0 must reproduce the baseline.

    OT_VME_BLDMA=all OT_VME_N=coll:1 PYTHONPATH=tools python3 -m hgi_sim.toksim_vme_compose_1020 \
        --measured results/token_pass/measured_hbm_1019/combined_1020/measured_rel_i8_su.json --bw 98 --bridge 1 --out X.json
"""
import json
import sys

from hgi_sim import d4g_reprice_1019 as R
from hgi_sim import d4g_vmearly_1019 as VME          # installs T.schedule = VME.schedule (+ RL knob capture)
from hgi_sim import toksim_hbm_census_1019 as C      # wraps it: _ORIG_SCHED = VME.schedule, T.schedule = C.schedule


def main():
    st = json.loads((R.ROOT / "results/arch/hbm_plan_study_1017/stages.json").read_text())
    VME._PLANB.update(st["plan_b"])
    rc = C.main()
    out = sys.argv[sys.argv.index("--out") + 1]
    doc = json.load(open(out))
    summ = {}
    for k, row in doc.get("table", {}).items():
        s = {}
        for side in ("ds", "qwen"):
            ra = row.get("rp_added_sum", {}).get(side, {})
            s[side] = {cl: dict(base=round(ra.get(f"vme:{cl}:base", 0.0), 1), exposed=round(ra.get(f"vme:{cl}:exposed", 0.0), 1),
                                records=ra.get(f"vme:{cl}:records", 0), raw_bound=ra.get(f"vme:{cl}:bound_raw", 0))
                       for cl in VME.CLIENTS}
        summ[k] = dict(ds_ar_tok_s=row.get("ds_ar_tok_s"), qwen_tok_s=row.get("qwen_tok_s"), clients=s)
    doc["vme"] = dict(issue_ahead=VME.N_OF, bl_dma=VME.BLDMA, layout=VME.LAYOUT, tool="tools/hgi_sim/toksim_vme_compose_1020.py")
    doc["vme_summary"] = summ
    json.dump(doc, open(out, "w"), indent=1, default=str)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
