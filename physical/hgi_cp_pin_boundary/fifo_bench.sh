#!/bin/bash
set -euo pipefail
scratch=$(mktemp -d /tmp/hgi-cp-fifo.XXXXXX)
trap 'rm -rf "$scratch"' EXIT
source_file=rtl/hbm_accel/generic/ot_hgi_cp.sv
if [ "${1:-exact}" = mutant ]; then
  python3 - "$source_file" "$scratch/mutant.sv" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text().replace('back_addr <= input_addr;', "back_addr <= 40'b0;")
Path(sys.argv[2]).write_text(s)
PY
  source_file=$scratch/mutant.sv
fi
iverilog -g2012 -DFETCH_SOURCE_SEAT=${SOURCE_SEAT:-0} -Irtl/hbm_accel/generic -o "$scratch/test.vvp" -s tb_fetch_fifo physical/hgi_cp_pin_boundary/tb_fetch_fifo.sv "$source_file" rtl/hbm_accel/generic/ot_hgi_seq.sv rtl/hbm_accel/generic/ot_hgi_cfg.sv
vvp -n "$scratch/test.vvp"
