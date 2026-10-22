#!/usr/bin/env python3
"""HBM-ELEM13/SMH-R7 r6: post-process the lp.py outputs of rp7_gen.py exactly as r5 did (rp5_reset_split.py), for all four
landed halves:
  * the landing writers use the r5 source-local per-slot reset capture (rtl/hbm_accel/sm/repack/h2a5/ot_rp5_land_reset_split.sv
    replaces rtl/common/landed_parent/ot_pl_land_reset_forest.sv: same primitive names, per-D4-slot kept rq copies, same edge);
  * every region whose plain scalar run lpr_<r> feeds >= 2 child reset pads gets one parallel forest leaf per pad at the SAME
    forest edge (r5 SMH_SCALAR_RESET_PARTITION, applied to every region instead of the two measured r5 ones);
  * the lp reset mutant already holds 64 stages (spec mut4_stages 64).
No data / reset / clock edge changes.

    python3 tools/hbm_sm_repack_1015/rp7_post.py
"""
from __future__ import annotations

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RTL = "rtl/hbm_accel/sm/repack/h2a7"
SPLIT = "rtl/hbm_accel/sm/repack/h2a5/ot_rp5_land_reset_split.sv"
FOREST = "rtl/common/landed_parent/ot_pl_land_reset_forest.sv"


def leaves_value(expr: str) -> int:
    e = re.sub(r"/", "//", expr)
    return int(eval(e, {"__builtins__": {}}))


def main():
    for h in "ns":
        for v in "mf":
            base = ROOT / RTL / f"lp_{h}_{v}"
            p = base / f"ot_hbm_smh_rp7{h}_{v}.sv"
            s = p.read_text()
            if "SMH_SCALAR_RESET_PARTITION" in s:
                print(f"{p.name}: already post-processed")
                continue
            regions = re.findall(r"localparam integer LPR_LEAVES_(\w+) = ", s)
            tot = 0
            for r in regions:
                pat = rf"\.d\(lpr_{r}\)"
                count = len(re.findall(pat, s))
                if count >= 2:
                    idx = iter(range(count))
                    s = re.sub(pat, lambda m: f".d(lpr_{r}_leaves[LPR_LEAVES_{r}-{count}+{next(idx)}])", s)
                    s, n = re.subn(rf"(localparam integer LPR_LEAVES_{r} = [^;]+)(;)",
                                   rf"\1+{count}\2 // SMH_SCALAR_RESET_PARTITION same existing leaf edge", s)
                    if n != 1:
                        raise SystemExit(f"{p}: missing LPR_LEAVES_{r}")
                m = re.search(rf"localparam integer LPR_LEAVES_{r} = ([^;]+);", s)
                lv = leaves_value(m.group(1))
                if lv > 1024:
                    raise SystemExit(f"{p}: region {r} {lv} leaves > 1024")
                tot += math.ceil(lv / 32)
                print(f"{p.name}: region {r} scalar pads {count} -> leaves {lv} ({math.ceil(lv / 32)} branches)")
            # With DEPTH=3 the shared root drives one prefix register per
            # region.  The old r6 DEPTH=2 root drove every branch directly.
            depth = re.search(r'ot_pl_land_reset_forest #\(\.DEPTH\((\d+)\)', s)
            actual_root_loads = len(regions) if depth and int(depth.group(1)) >= 3 else tot
            if actual_root_loads > 32:
                raise SystemExit(f"{p}: forest root loads {tot} > 32")
            print(f"{p.name}: forest root loads {actual_root_loads}")
            if "SMH_SCALAR_RESET_PARTITION" not in s:
                s = s.replace("\nmodule ", "\n// SMH_SCALAR_RESET_PARTITION: no region needed a partition\nmodule ", 1)
            p.write_text(s)
            b = base / f"ot_hbm_smh_rp7{h}_{v}_bench.sh"
            t = b.read_text()
            if FOREST in t:
                t = t.replace(FOREST, SPLIT)
                b.write_text(t)


if __name__ == "__main__":
    main()
