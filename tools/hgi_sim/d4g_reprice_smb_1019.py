#!/usr/bin/env python3
"""HBM-SMBUDGET (10-19): the d4g token re-priced with the relative SM service (coordinator decision 0jx: C + C2 + P2 +
2,048-word programme store) and the Qwen INT8 SM path, on top of HBM-REPRICE's model (tools/hgi_sim/d4g_reprice_1019.py,
claude/hbm-reprice-1019 3e3fd2aa0; the fleet bundle copy is imported unchanged, only its TERMS are set here).

Terms changed (each with its evidence):
  att_desc  640 -> 0     MEASURED (RTL): the issuer descriptors are token-resident and relative (C: layer stride; window
                         base via HBM-ATTGAP window staging, 0 critical cycles) -- no per-layer table rewrite, no run lock.
                         smb_unit pos/L14 benches: every go on its compiler slot from ONE install.
  att_prog  0 (unchanged value, now RTL-backed): the 2,048-word store holds the resident QK+PV programmes (1,019 words,
                         HBM-ATTGAP) beside all DS matvec bodies (152 words) -> BIGPROG form, no S32 sub-runs, no reinstall.
  sm_svc    NEW, PRICED (RTL-measured structure): a block programme (one group-slot wave) occupies 64 positional issue
                         edges + 6 go/done edges on the SM (smb_unit benches); the HBM price charges 1.375 edges a line, so
                         a partial wave costs max(0, 70 - 1.375 x lines) more: per layer kind (L00 310 / L02 384 / L14 388,
                         head 4), busiest SM, fully exposed (conservative); the as-built one-go-per-block service had the
                         same granularity unpriced.
  qwen_int8 NEW, MEASURED: Qwen SM.MATVEC on the INT8 path of the die SM (SMB-INT8, claude/smb-int8-1019): every op of
                         layer 0 within its price (24,067 vs 24,938 cycles) -> 0 cycles (the price already charges INT8 bytes).

  PYTHONPATH=tools python3 -m hgi_sim.d4g_reprice_smb_1019 --smb SMB_POS_JSON --jobs 40 --out price_smb.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hgi_sim import d4g_reprice_1019 as R

DS_LAYERS = 43          # DS V4.1 decode layers of the AR token (token_compose hds_sched)


def sm_svc_cycles(g):
    """per-token SM-service block-granularity excess (smb_unit P2 blocks): per layer kind sum over blocks of
    max(0, 70 - 1.375 x lines) (a block programme occupies 64 positional issue edges + 6 go/done edges; the HBM price
    charges 1.375 edges a line), busiest SM, exposed in full (conservative); MoE layers take the worst kind."""
    kinds = {k: v["excess"] for k, v in g.items() if k != "head"}
    per = max(kinds.values())
    return dict(per_layer_kind=kinds, per_layer=per, head=g["head"]["excess"], token=DS_LAYERS * per + g["head"]["excess"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--smb", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=40)
    a = ap.parse_args()
    sv = sm_svc_cycles(json.loads(a.smb.read_text()))
    R.TERMS["att_desc"] = (0, "measured", "0: token-resident relative descriptors (C) + window staging",
                           "HBM-SMBUDGET claude/hbm-smbudget-1019 smb_unit (issuer_rel), HBM-ATTGAP staging")
    R.TERMS["att_prog"] = (0, "measured", "0: 2,048-word store holds QK+PV (1,019) + every DS matvec body (152)",
                           "HBM-SMBUDGET ot_smh_calendar_static_x AW 11, smb_unit budget")
    R.TERMS["sm_svc"] = (sv["token"], "priced", f"+{sv['per_layer']:.0f} a layer x {DS_LAYERS} + head {sv['head']:.0f} "
                         "(SM.MATVEC spans through the relative svg service over price, exposed)",
                         "HBM-SMBUDGET smb_unit pos (tb_hbm_svg_rel_sm, die SM master)")
    R.TERMS["qwen_int8"] = (0, "measured", "0: Qwen INT8 SM.MATVEC within price on the die SM INT8 path",
                            "SMB-INT8 claude/smb-int8-1019 0e80758d9 (results/rtl/hbm_qwen_layer_tput_1018/smb_int8_1019)")
    # att_desc = 0: dropped from the composition (the pool workers read the module TERMS of their own import)
    R.COMPOSED[:] = [t for t in R.TERMS if t != "att_desc"]
    prev = R.post_hoc

    def post_hoc(row, terms):
        ar, qc = prev(row, terms)
        if "sm_svc" in terms:
            ar += R.TERMS["sm_svc"][0]
        return ar, qc
    R.post_hoc = post_hoc
    orig_with = R.with_terms

    def with_terms(base, terms, **extra):
        k = orig_with(base, [t for t in terms if t not in ("sm_svc", "qwen_int8")], **extra)
        k["_terms"] = sorted(terms)
        return k
    R.with_terms = with_terms
    sys.argv = [sys.argv[0], "--jobs", str(a.jobs), "--out", str(a.out)]
    rc = R.main()
    doc = json.loads(a.out.read_text())
    doc["smbudget"] = dict(sm_svc=sv, note=__doc__)
    a.out.write_text(json.dumps(doc, indent=1, default=str) + "\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
