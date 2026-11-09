#!/usr/bin/env python3
"""DIE-HBM-92-OPEN/ROOTG1C (11-08, DIE-HBM-92 ruling (c)): right-width 128x128 master for ot_wbq_root_g1.

ot_wbq_root_g1 holds 4 lane payloads of 128 words x 256 bits (ot_sram_1r1w_128x256_m1_r0c0_g256, 91.8 x 27.576 um, 265 M4
pins per short edge). In the 216 x 129.6 slot no orientation of that master routes: an R0/MY tower leaves one port
behind the tower (GRT overflow 9887 on M6) and an R90 tower puts all edge pins on one M4 row (DRT-0073). Each lane
payload becomes two 128 x 128 halves (lo = bits 127:0, hi = bits 255:128), the same words, address, one-cycle
registered read and single mask pin as the 128x256, so two facing 4-row towers fit with a central write channel.

Same generator flow as build_hbm_rightwidth_1103.py (sram_gen + aligned v2, pin faces rw, scalar mask); only the new
master is built, the existing masters are not regenerated.

    python3 tools/mem_compiler/build_hbm_rootg1c_1108.py [--dry]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_hbm_rightwidth_1103 as rw  # noqa: E402

SPECS = [
    ("ot_sram_1r1w_128x128_m1_r0c0_g128", 128, 128, 1, 128, {"ot_wbq_root_g1": 8}),
]


def build(root, dry=False):
    saved = rw.SPECS
    rw.SPECS = SPECS
    try:
        return rw.build(root, dry=dry)
    finally:
        rw.SPECS = saved


if __name__ == "__main__":
    dry = "--dry" in sys.argv[1:]
    out, rows = build(Path(__file__).resolve().parents[2], dry=dry)
    print(json.dumps({"out": str(out), "masters": rows}, indent=1))
