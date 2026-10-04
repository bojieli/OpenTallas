#!/usr/bin/env python3
"""hbm-fmax-su (2026-10-04): the DS HBM serial unit's chain benches at the 1.2 GHz depths.

A thin driver over tools/dshbm_baseline_measure.py (su-run / su-equiv, unchanged): with --f12 the RTL source list
takes the 1.2 GHz file swaps (rtl/hdc/ot_hdc_fastfp_lat_f12.sv + rtl/hdc/ot_hdc_fp32_f12.sv in place of
rtl/hdc/ot_hdc_fastfp_lat.sv; every --swap OLD=NEW likewise), so `--fp rtl` runs the bit-level units that close
0.833 ns.  The DPI runs (--fp dpi / dpi_beh) are latency-only stand-ins: their cycles depend on MLAT / ALAT /
BCAST / RET alone, so they are the same for either source list.

    python3 tools/su_fmax_measure.py su-run --out O --work W --bcast 7 --ret 8 --mlat 5 --alat 4 --n 1024 --m 256 \
        --fp dpi_beh --cases su_cases_v2.pkl
    python3 tools/su_fmax_measure.py su-run --f12 ... --n 64 --m 16 --fp rtl --cases su_cases_v2.pkl
    python3 tools/su_fmax_measure.py su-equiv --out O --su RTL.json,DPI.json --record EQ.json
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

F12_SWAP = {"rtl/hdc/ot_hdc_fastfp_lat.sv": ["rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_fp32_f12.sv"]}


def apply_swaps(swaps):
    import rtl_hdc_v41x_vec_campaign as VC
    for lst in (VC.RTL, VC.LIB):
        out = []
        for p in lst:
            r = str(Path(p).relative_to(ROOT))
            out += [ROOT / x for x in swaps[r]] if r in swaps else [p]
        lst[:] = out
    for new in [x for v in swaps.values() for x in v]:
        assert (ROOT / new).is_file(), new


def main():
    argv = sys.argv[1:]
    swaps = {}
    if "--f12" in argv:
        argv.remove("--f12")
        swaps.update(F12_SWAP)
    while "--swap" in argv:
        i = argv.index("--swap")
        old, new = argv[i + 1].split("=", 1)
        swaps.setdefault(old, []).extend(new.split(","))
        del argv[i:i + 2]
    if swaps:
        apply_swaps(swaps)
        print("source swaps:", {k: v for k, v in swaps.items()}, flush=True)
    sys.argv = [str(ROOT / "tools/dshbm_baseline_measure.py")] + argv
    import runpy
    runpy.run_path(str(ROOT / "tools/dshbm_baseline_measure.py"), run_name="__main__")


if __name__ == "__main__":
    main()
