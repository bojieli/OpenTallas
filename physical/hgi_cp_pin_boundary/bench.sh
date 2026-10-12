#!/bin/bash
set -euo pipefail
mode=${1:-exact}
benchdir=rtl/hbm_accel/generic/tb
scratch=$(mktemp -d /tmp/hgi-cp-fetch-pin.XXXXXX)
trap 'rm -rf "$scratch"' EXIT
case "$mode" in exact) extra=();; conformance) extra=(-DSEQ_CONF);; mutant) extra=(-DOT_HGI_SEQ_MUT_TOKX);; mutfq) extra=(); export CP_MUT_FQ=1;; *) exit 2;; esac
[ "${CP_FQ:-1}" = 1 ] && extra+=(-DCP_FQ_LOCAL)
python3 - "$benchdir/tb_hgi_seq.sv" "$scratch/tb.sv" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
import os
fq=os.environ.get('CP_FQ','1')
mut=os.environ.get('CP_MUT_FQ','0')
s=s.replace('ot_hgi_cp #(.USE_MACRO(', 'ot_hgi_cp #(.FETCH_PIN_FIFO(1), .FQ_LOCAL(%s), .MUT_FQ(%s), .USE_MACRO(' % (fq, mut))
Path(sys.argv[2]).write_text(s)
PY
cd "$benchdir"
iverilog -g2012 -DSEQ_CP -DSEQ_MACRO "${extra[@]}" -I. -I.. -o "$scratch/sim.vvp" -s tb_hgi_seq "$scratch/tb.sv" ../ot_hgi_seq.sv ../ot_hgi_cp.sv ../ot_hgi_cfg.sv ../../../../physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v ../../../../physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
vvp -n "$scratch/sim.vvp" | tee "$scratch/sim.log"
# [cp] a FAIL verdict is a nonzero exit (the loop judges expect=fail benches by rc as well as the regex)
grep -q "HGI_SEQ PASS" "$scratch/sim.log"
