#!/usr/bin/env python3
"""ot_gpu_cdc_fifo_oh on the unmodified CDC FIFO bench (rtl/test/gpu_sys/tb_gpu_cdc_fifo.sv, tools/gpu_sys/run_cdc_fifo.py):
a generated copy of the bench instantiates the successor for its ENABLE=1 FIFOs (integrity over 20,000 entries per
clock pair and depth, measured rates vs the sizing model, overflow fault); run_cdc_fifo's own checks decide.

    python3 run_cdc_fifo_oh.py --out cdc_fifo_oh.json --build-dir DIR [--wdup 8]   (run on a compute host)
The lint verdict flags DECLFILENAME only (ot_link_afifo_oh / ot_gpu_kreg_oh share the file, as ot_gpu_sys_glue.sv does).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools" / "gpu_sys"))
import run_cdc_fifo as RC  # noqa: E402

bdir = Path(sys.argv[sys.argv.index("--build-dir") + 1])
wdup = int(sys.argv[sys.argv.index("--wdup") + 1]) if "--wdup" in sys.argv else 0
if "--wdup" in sys.argv:
    i = sys.argv.index("--wdup"); del sys.argv[i:i + 2]
bdir.mkdir(parents=True, exist_ok=True)
tb = RC.BENCH.read_text()
n = tb.count("ot_gpu_cdc_fifo #(.ENABLE(1)")
assert n == 3, n            # two ENABLE=1 instances + the header comment
(bdir / "tb_gpu_cdc_fifo.sv").write_text(tb.replace("ot_gpu_cdc_fifo #(.ENABLE(1)", f"ot_gpu_cdc_fifo_oh #(.WDUP({wdup}), .ENABLE(1)"))
RC.BENCH = bdir / "tb_gpu_cdc_fifo.sv"
RC.RTL = RC.RTL + [ROOT / "rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv"]
sys.exit(RC.main())
