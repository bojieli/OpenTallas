#!/bin/bash
# Run this from scratch2 under ot-run (8GB, one thread); original proof logs are preserved.
set -eu
cd "$(dirname "$0")"
python3 - <<'PYGEN'
from pathlib import Path
for case in ('bf16_5', 'bf16_6', 'fp32_6', 'wrong32_6'):
    text = Path(case + '.ys').read_text().splitlines()
    text[0] = 'read_verilog -sv -defer -D SYNTHESIS -D OT_S81_VE_LOADSAFE5 /work/rtl/ot_s81sl_ve_fp.sv /work/rtl/ot_hdc_fastfp.sv /work/rtl/ot_hdc_prefix.sv /work/top.sv'
    text[-1] = text[-1].replace('/work/' + case + '.cex.json', '/work/' + case + '.minimal.cex.json')
    Path(case + '.minimal.ys').write_text('\n'.join(text) + '\n')
PYGEN
for case in bf16_5 bf16_6 fp32_6 wrong32_6; do
    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -s "/work/$case.minimal.ys" >"$case.minimal.log" 2>&1
done
