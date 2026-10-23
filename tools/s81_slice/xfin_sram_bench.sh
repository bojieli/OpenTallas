#!/usr/bin/env bash
# Existing source/golden mechanism, only add opt-in files/define and pin5.050.
set -euo pipefail
kind=${1:?norm or eng};out=${2:?out};shift 2
mkdir -p "$out"
python3 - "$kind" "$out" "${XFIN_DEFS:-OT_S81DV_XFIN_SRAM}" <<'P'
from pathlib import Path
import sys
kind,out,defs=sys.argv[1:]
df=' '.join('+define+'+d for d in defs.split())
name='norm16_bench.sh' if kind=='norm' else 'xfin_eng_bench.sh'
p=Path('tools/s81_dv')/name
if not p.exists():p=Path('tools/s81_slice')/name
s=p.read_text()
extra='rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv rtl/dsrom_sys/s81_dv/ot_s81dv_fp_n32.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v '
s=s.replace('srcs="','srcs="'+extra,1)
s=s.replace('$DEF --top-module',df+' $DEF --top-module').replace('$DEF -GORD=', df+' $DEF -GORD=')
s=s.replace('verilator --binary','"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary')
# STW-S81e-COLLA2 10-23: XFIN_VFLAGS (e.g. -fno-dfg, as the N26 equivalence vehicle): Verilator 5.050 DFG internal fault on the N26 eng build
vf=__import__('os').environ.get('XFIN_VFLAGS','')
if vf: s=s.replace('--binary','--binary '+vf).replace('$V --binary','$V --binary')
Path(out,'existing_runner.sh').write_text(s)
P
J=${J:-8} bash "$out/existing_runner.sh" "$out" "$@"
