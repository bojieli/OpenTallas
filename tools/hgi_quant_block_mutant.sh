#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
python3 - "$out/accept_wrong_block.sv" <<'MUTATE'
from pathlib import Path
import sys
s=Path('rtl/hbm_accel/generic/ot_hgi_quant_decode.sv').read_text()
old='op==6 && header[71:64]==16'
assert s.count(old)==1
Path(sys.argv[1]).write_text(s.replace(old,'op==6'))
MUTATE
hdc=(rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_prefix.sv)
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hgi_quant_decode -Mdir "$out/mutant.obj" -o sim "${hdc[@]}" physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv physical/hbm_accel_die_views/quant/rtl/ot_hfd_actquant_m.sv rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv "$out/accept_wrong_block.sv" rtl/test/hbm_accel/generic/tb_hgi_quant_decode.sv > "$out/mutant.build" 2>&1
set +e
"$out/mutant.obj/sim" > "$out/mutant.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$out/mutant.rc"
[[ $rc -ne 0 ]] && grep -q 'DECODE mismatch' "$out/mutant.log"
