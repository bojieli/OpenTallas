#!/usr/bin/env python3
"""H-MTP2/idx: verify-cycle sensitivity of the IDX P-row family to the MEASURED IDX.TOPK row II.

Times the batched verify (P = 6, fixed price table, item set COLL+FUSED+HC+SU_DMA[+IDX]) with hgi_sim.ds_mtp_rows._job,
replacing ds_mtp_verify.row_ii's IDX.TOPK II (model 47) by a given value; IDX.INDEX optionally serial (II = c1).

    PYTHONPATH=src python3 tools/hbm_idx_rows_sens.py OUT.json [label:topk_ii[:serial]] ...     (from the repo root)
    label 'none' = item set without IDX (no IDX P-row records)
"""
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from hgi_sim import ds_mtp_verify as V  # noqa: E402
from hgi_sim import ds_mtp_rows as R  # noqa: E402

ORIG = V.row_ii
ITEMS = ("COLL", "FUSED", "HC", "SU_DMA", "IDX")


def run(label, topk_ii, index_serial):
    def rii(r, c1, dyn, L, sk_rep=3):
        fam = V.row_family(r)
        if fam == "IDX.TOPK" and topk_ii is not None:
            return topk_ii, topk_ii, "patched (measured)"
        if fam == "IDX.INDEX" and index_serial:
            return c1, c1, "patched serial"
        return ORIG(r, c1, dyn, L, sk_rep)
    V.row_ii = rii
    its = ITEMS if label != "none" else ITEMS[:-1]
    _, r = R._job((label, its, 6, "fixed", None))
    return r["cycles"]


def main():
    out = {}
    for spec in sys.argv[2:]:
        f = spec.split(":")
        label = f[0]
        ii = float(f[1]) if len(f) > 1 and f[1] else None
        out[label] = dict(topk_ii=ii, index_serial=len(f) > 2, verify_cycles=run(label, ii, len(f) > 2))
        print(label, out[label], flush=True)
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
