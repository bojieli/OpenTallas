#!/usr/bin/env bash
set -euo pipefail
R=$(pwd);mkdir -p equiv;cd src
python3 - "$R" <<'P'
from pathlib import Path
import sys
r=Path(sys.argv[1]);s=Path('rtl/test/tb_dsrom_fp32_add_l6.sv').read_text()
for k in ['add','mul']:
 t=s.replace('ot_dsrom_fp32_add_f12_l6 u6','ot_s81sl_fp_'+k+'_n32 u6')
 if k=='mul':t=t.replace('ot_hdc_fp32_add_fast','ot_hdc_fp32_mul_fast')
 t='\n'.join(l.replace('.rst_n(rst_n)', '.rst_n({6{rst_n}})') if 'u6 (' in l else l for l in t.splitlines())+'\n'
 (r/'equiv'/('tb_'+k+'.sv')).write_text(t)
P
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for k in add mul;do
 "$V" --cc --exe --build -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_dsrom_fp32_add_l6 --Mdir "$R/equiv/$k" "$R/equiv/tb_$k.sv" rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_fp_n32.sv "$R/src/rtl/test/tb_dsrom_fp32_add_l6.cpp" -o sim > "$R/equiv/$k.build.log" 2>&1
 "$R/equiv/$k/sim" 2000000 12345 > "$R/equiv/$k.log" 2>&1
 cat "$R/equiv/$k.log"
done
