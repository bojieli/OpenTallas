#!/usr/bin/env python3
"""TOK-HBM (10-24): bracket the token price of the r18h5 transport repairs on top of the P7 + leaf-split price.

The token gate found two die-level transport defects (results/token_pass/tok_hbm_1024/README.md): SU programme/config
ports land 29..55 serial edges after the root (compiler assumes a 9-edge start advance), and the HC root <-> quarter
links carry 8..10 relay edges each way with hc_eng still bound XRD = XRU = 0.  The candidate repairs
(results/token_pass/codex_hbm_prog_r8_1024, codex_hbm_hc_r8_candidate_1024) are: every SU command bundle padded to 61
serial edges (root advance 113 serial instead of 9), and HC XRD = XRU = 10 (+20 HC unit edges per HC_MIX round trip).

This module stacks per-record exposures on hgi_sim.leaf_split_price_1023 (which itself stacks on plan_study_price_1017):
    OT_HBM_XFIX_SU   serial edges added to every SU-executed record (d4g_quadrant_1017.su_exec); 0 = the compiler
                     issues each programme the full root advance earlier (fully hidden), 104 = fully exposed
                     (113 - 9 required vs compiled start advance)
    OT_HBM_XFIX_HC   serial edges added to every HC.HC_MIX / HC.HC_MIX_POST record (20 = XRD + XRU)
Serial edges -> 1.2 GHz stream cycles x 4/3 (same rule as leaf_split_price_1023).

    OT_HBM_LEAF_SPLIT=1 OT_HBM_XFIX_SU=104 OT_HBM_XFIX_HC=20 PYTHONPATH=tools \
        python3 -m hgi_sim.transport_fix_price_1024 --stages S.json --x-c 377.6 --out O.json
"""
from __future__ import annotations

import os
import sys

from hgi_sim import leaf_split_price_1023 as LSP
from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import d4g_quadrant_1017 as Q

SU = float(os.environ.get("OT_HBM_XFIX_SU", "0"))
HC = float(os.environ.get("OT_HBM_XFIX_HC", "0"))
_ADDED = LSP.added


def added(r):
    a, why = _ADDED(r)
    why = [why] if why else []
    op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
    if SU and Q.su_exec(r):
        a += SU * LSP.SERIAL; why.append("xsu")
    if HC and op in ("HC.HC_MIX", "HC.HC_MIX_POST"):
        a += HC * LSP.SERIAL; why.append("xhc")
    return a, "+".join(why) or None


LSP.added = added

if __name__ == "__main__":
    print(f"XFIX su={SU} hc={HC} serial edges; leaf_split={LSP.LS.enabled()}", file=sys.stderr)
    rc = PS.main()
    print(f"XFIX record hits {dict(LSP.HITS)}", file=sys.stderr)
    raise SystemExit(rc)
