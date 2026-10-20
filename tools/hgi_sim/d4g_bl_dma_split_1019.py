#!/usr/bin/env python3
"""HBM-VMEARLY-DMA (10-19): which DS records really pay the DMA-back VM round trip (bl_dma, 'DMA lag83 + g4 10').

d4g_reprice3_1019 charges INFO term bl_dma = VM_HBM 93/2 on EVERY DMA record (ds_relay_latency.crossings: LOAD x1
request, FENCE x1, KVWB/STORE x1).  The 93 is the DMA-BACK controller's issue->drain lag (ot_hgi_dma_back_static_vp4_*,
RR_RT 80 + 3, + VM glue g4 10): only VM->HBM moves (KVWB_DS window_row_append, STORE, swap-out) read VM banks through it.
DMA.LOAD (HBM->VM table loads) and DMA.FENCE never issue a dbk VM read.

  --mode all    reprice3 as committed (bl_dma on every DMA record)
  --mode kvwb   bl_dma only on VM-read DMA records (KVWB*/STORE/swap-out); LOAD/FENCE keep the plan_b VM_HBM stage

    PYTHONPATH=tools python3 -m hgi_sim.d4g_bl_dma_split_1019 --mode kvwb --out OUT.json --only info_bl_dma,info_banklat_all
"""
from __future__ import annotations
import sys
from hgi_sim import ds_relay_latency as RL

BL_DMA = 93 / 2


def main():
    mode = 'all'
    if '--mode' in sys.argv:
        i = sys.argv.index('--mode')
        mode = sys.argv[i + 1]
        del sys.argv[i:i + 2]
    if mode == 'kvwb':
        orig_cross, orig_knob = RL.crossings, RL._knob

        def crossings(r, upper=False):
            c = orig_cross(r, upper)
            op = getattr(r, 'orig_op', f'{r.unit}.{r.op}')
            u, o = op.split('.', 1)
            if op == 'DMA.SWAP':
                o = 'LOAD' if 'in' in (r.tag or '').split()[-1] else 'STORE'
            if u == 'DMA' and o in ('LOAD', 'FENCE') and 'VM_HBM' in c:
                c = dict(c)
                c['VM_HBM_RQ'] = c.pop('VM_HBM')        # request leg only: no dbk VM-bank read
            return c

        def knob(b, o, only=None):
            b2, o2 = dict(b), dict(o)
            b2['VM_HBM_RQ'] = b.get('VM_HBM', 0.0)
            ov = o.get('VM_HBM', 0.0)
            # the bl_dma stage override replaces plan_b's VM_HBM; the request leg keeps plan_b's own value
            o2['VM_HBM_RQ'] = PLAN_B_VM_HBM if abs(ov - BL_DMA) < 1e-9 else ov
            return orig_knob(b2, o2, only)
        RL.crossings, RL._knob = crossings, knob
    elif mode != 'all':
        raise SystemExit(f'unknown mode {mode}')
    from hgi_sim import d4g_reprice3_1019 as R3
    return R3.main()


import json as _json
from pathlib import Path as _P
PLAN_B_VM_HBM = _json.loads((_P(__file__).resolve().parents[2] / 'results/arch/hbm_plan_study_1017/stages.json')
                            .read_text())['plan_b']['VM_HBM']

if __name__ == '__main__':
    raise SystemExit(main())
