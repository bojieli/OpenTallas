#!/usr/bin/env python3
"""CLAUDE S81-PH su/hc: exact bench of the REMOTE-READ SU split (ot_s81ph_su_xing) inside the unchanged V4.1x decode core.

Runs tools/rtl_hdc_v41x_decode_campaign.py (single bit-exact decode step, --units su: every SU op of a real token
program, checked against the ISA model: logits, vector memory, KV cache) with ot_hdc_v41x_su_adapt replaced by the
bench shim (rtl/dsrom_sys/s81_ph/test/ot_hdc_v41x_su_adapt_s81ph_shim.sv -> ot_s81ph_su_xing -> ot_s81ph_su_adapt ->
ot_s81ph_vec / ot_s81ph_vec_lane) at +define+S81PH_DF / S81PH_DR / S81PH_NEG.

usage: su_split_bench.py [--unit su|he] --df 3 --dr 3 [--neg 0] --out DIR [campaign args...]
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_decode_campaign as C

ap = argparse.ArgumentParser()
ap.add_argument("--df", type=int, required=True)
ap.add_argument("--dr", type=int, required=True)
ap.add_argument("--neg", type=int, default=0)
ap.add_argument("--unit", choices=("su", "he"), default="su")
ap.add_argument("--out", type=Path, required=True)
a, rest = ap.parse_known_args()
SPLIT = {"su": ("ot_hdc_v41x_su_adapt", ["rtl/dsrom_sys/s81_ph/su/ot_s81ph_vec_lane.sv", "rtl/dsrom_sys/s81_ph/su/ot_s81ph_vec.sv",
                                         "rtl/dsrom_sys/s81_ph/su/ot_s81ph_su_adapt.sv", "rtl/dsrom_sys/s81_ph/su/ot_s81ph_su_xing.sv",
                                         "rtl/dsrom_sys/s81_ph/test/ot_hdc_v41x_su_adapt_s81ph_shim.sv"]),
         "he": ("ot_hdc_v41x_he_adapt", ["rtl/dsrom_sys/s81_ph/hc/ot_s81ph_he_adapt.sv", "rtl/dsrom_sys/s81_ph/hc/ot_s81ph_he_xing.sv",
                                         "rtl/dsrom_sys/s81_ph/test/ot_hdc_v41x_he_adapt_s81ph_shim.sv"])}
nat, files = SPLIT[a.unit]
i = C.RTL.index(ROOT / f"rtl/hdc/v41x/{nat}.sv")
C.RTL[i:i + 1] = [ROOT / f for f in files]
# the current tb_hdc_core_v41x.sv names the pooled index unit hierarchically: its modules must exist even when unused
C.RTL.extend(ROOT / f"rtl/hdc/v41x/{n}.sv" for n in (
    "ot_hdc_v41x_idx_pcol", "ot_hdc_v41x_idx_hsum", "ot_hdc_v41x_idx_pool_finish", "ot_hdc_v41x_idx_pool_batch",
    "ot_hdc_v41x_idx_pool_replica", "ot_hdc_v41x_idx_pool_adapt", "ot_hdc_v41x_idx_pool_kwr", "ot_hdc_v41x_idx_pool_hbm_bridge"))
_defs = C.defines
C.defines = lambda lanes=None: _defs(lanes) + [f"+define+S81PH_DF={a.df}", f"+define+S81PH_DR={a.dr}", f"+define+S81PH_NEG={a.neg}"]
a.out.mkdir(parents=True, exist_ok=True)
tag = f"{a.unit}_df{a.df}_dr{a.dr}_neg{a.neg}"
sys.argv = [sys.argv[0], "--units", a.unit, "--single-only", "--output", str(a.out / f"{tag}.json"), *rest]
rc = C.main()
print("S81PH_SU_BENCH", tag, "rc", rc)
sys.exit(rc)
