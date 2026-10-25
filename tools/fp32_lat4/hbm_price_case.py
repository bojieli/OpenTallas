#!/usr/bin/env python3
"""FP32 lane (10-24) what-if wrapper on the HBM price of record (hgi_sim.leaf_split_price_1023, P7 stages_g675).

Env knobs (all default to the price of record):
  FP_ALAT      SU depth-model FP32 add latency (hbm_su_c12.P['alat'], record 6 = c12 build at 1.2 GHz)
  FP_MLAT      SU depth-model FP32 mul latency (hbm_su_c12.P['mlat'], record 6)
  FP_SU_SCALE  multiply every timing.su_cost result (1.0 record; 4/3 = SU issue + depth in 0.9 GHz serial cycles)
  FP_SERIAL    leaf-split serial->stream factor (leaf_split_price_1023.SERIAL, record 4/3; 1.0 = serial units on 1.2 GHz)
Run: OT_HBM_LEAF_SPLIT=1 PYTHONPATH=<wt>/tools python3 hbm_fp32_case.py --stages S --x-c 377.6 --out O
"""
import os
import sys

import hbm_su_c12 as C12
from hgi_sim import timing as T
from hgi_sim import leaf_split_price_1023 as LSP
from hgi_sim import plan_study_price_1017 as PS

C12.P["alat"] = int(os.environ.get("FP_ALAT", C12.P["alat"]))
C12.P["mlat"] = int(os.environ.get("FP_MLAT", C12.P["mlat"]))
SCALE = float(eval(os.environ.get("FP_SU_SCALE", "1.0")))
LSP.SERIAL = float(eval(os.environ.get("FP_SERIAL", "4/3")))
_ORIG = T.su_cost


def su_cost(r, dyn, L):
    c, how = _ORIG(r, dyn, L)
    return c * SCALE, how + (f" x{SCALE:.4f}" if SCALE != 1.0 else "")


T.su_cost = su_cost
print(f"FP32 case alat={C12.P['alat']} mlat={C12.P['mlat']} su_scale={SCALE} serial={LSP.SERIAL}", file=sys.stderr)
raise SystemExit(PS.main())
