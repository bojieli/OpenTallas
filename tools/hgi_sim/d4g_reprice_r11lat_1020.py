#!/usr/bin/env python3
"""HBM-SUPROF (10-20): price of record (d4g_reprice3c_1019, L2H-BW face p540 successor, DS 1406.1 / Qwen 746.5) + the
GEN2e4 r11 die bank-client latency budget raises that S8b l12_banklat needs on the emitted r11 geometry (both plans A/B,
results/arch/hbm_die_d4g/gen2e4r11_1020/l12_budget_r11.json).  Each raise is a static, compile-time fixed latency (no
flow control); the compiler/die schedule carries it, priced here fully exposed once per record (upper bound):
  r11_hc_tap   HC LG tap term READ_RETURN 32->34 / WRITE_RETURN 29->31 (+ qhub RD_CAPTURE/GATHER 37->39, DONE 33->35):
               +2 an HC record reading VM, +2 an HC record writing VM (HC.HC_MIX, HC.HC_MIX_POST, FUSED.HC_PRE_NORM,
               FUSED.HC_POST, unit HC).
  r11_qdq      hb_quant_NW RL 45->57: +12 a FUSED.QDQ* record (unit QDQ too).
  r11_argmax   hb_argmax VMX 77->78: +1 an ARGMAX record.
  r11_coll     hcollrs_SW BANK_RT 72->73: +1 a COLL record reading VM (slowest quadrant sets the collective).
  r11_xload    xl ctlx RD_LAT bank1 39->40: 0 (x-load priced at max RD_LAT 55, unchanged).
    PYTHONPATH=tools python3 -m hgi_sim.d4g_reprice_r11lat_1020 --bw 90.67 --bridge 1 --face p540 --out r11.json
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from hgi_sim import d4g_reprice_1019 as R
from hgi_sim import d4g_reprice3c_1019 as R3C

R11 = dict(hc=2, qdq=12, argmax=1, coll=1)
HC_OPS = ("HC.HC_MIX", "HC.HC_MIX_POST", "FUSED.HC_PRE_NORM", "FUSED.HC_POST")
SRC = "HBM-SUPROF 10-20 l12 probe on r11 contract_pre A/B (results/arch/hbm_die_d4g/gen2e4r11_1020/l12_budget_r11.json)"


def _op(r):
    return getattr(r, "orig_op", f"{r.unit}.{r.op}")


def main():
    true_main = R.main

    def hook():
        R.TERMS["r11_hc_tap"] = (R11["hc"], "priced", "+2 an HC record reading VM, +2 writing VM (tap term 34/31 vs 32/29)", SRC)
        R.TERMS["r11_qdq"] = (R11["qdq"], "priced", "+12 a QDQ record (hb_quant_NW RL 57 vs 45)", SRC)
        R.TERMS["r11_argmax"] = (R11["argmax"], "priced", "+1 an ARGMAX record (VMX 78 vs 77)", SRC)
        R.TERMS["r11_coll"] = (R11["coll"], "priced", "+1 a COLL record reading VM (hcollrs_SW BANK_RT 73 vs 72)", SRC)
        for t in ("r11_hc_tap", "r11_qdq", "r11_argmax", "r11_coll"):
            if t not in R.COMPOSED:
                R.COMPOSED.append(t)
        inner = R.rp_added

        def rp_added(r, c, kn):
            add = inner(r, c, kn)
            rp = kn.get("rp") or set()
            op = _op(r)
            if "r11_hc_tap" in rp and (r.unit == "HC" or op in HC_OPS):
                v = (R11["hc"] if R._reads_vm(r) else 0) + (R11["hc"] if R._writes_vm(r) else 0)
                if v:
                    add += v; R._add("r11_hc_tap", v)
            if "r11_qdq" in rp and (r.unit == "QDQ" or op.startswith("FUSED.QDQ")):
                add += R11["qdq"]; R._add("r11_qdq", R11["qdq"])
            if "r11_argmax" in rp and r.unit == "ARGMAX":
                add += R11["argmax"]; R._add("r11_argmax", R11["argmax"])
            if "r11_coll" in rp and r.unit == "COLL" and R._reads_vm(r):
                add += R11["coll"]; R._add("r11_coll", R11["coll"])
            return add
        R.rp_added = rp_added
        return true_main()

    R.main = hook
    rc = R3C.main()
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    doc = json.loads(out.read_text())
    doc["lane"] = "HBM-SUPROF"
    doc["tool"] = "tools/hgi_sim/d4g_reprice_r11lat_1020.py (wraps d4g_reprice3c_1019.py)"
    doc["r11_terms"] = dict(R11, source=SRC)
    out.write_text(json.dumps(doc, indent=1, default=str) + "\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
