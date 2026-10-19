#!/bin/bash
set -euo pipefail
for override in NTX=4 PR=0 SAFE_RC=0 TXDP=50529301; do
 n=${override%=*}
 if iverilog -g2012 -s qkd_d2d_static_ovl_reset24 -Pqkd_d2d_static_ovl_reset24.$override -o bad_${n}.sim functional_cells_udp.v sram.v ovl_reset24.v > bad_${n}.log 2>&1; then echo "BAD profile admitted: $override";exit 1; fi
 grep -q invalid_kv_d2d_reset24_profile bad_${n}.log
done
for mut in polarity missing late; do
 python3 - "$mut" <<'PY'
from pathlib import Path
import re,sys
s=Path('ovl_reset24.v').read_text();m=re.search(r'(always @\(posedge ck\) kv_reset_copy_0_0 <= )([^;]+);',s);assert m
if sys.argv[1]=='polarity':new=m[1]+'~('+m[2]+' );'
elif sys.argv[1]=='missing':new=m[1]+"1'b1;"
else:new='reg delayed_reset_mut; always @(posedge ck) delayed_reset_mut <= '+m[2]+';\n'+m[1]+'delayed_reset_mut;'
s=s[:m.start()]+new+s[m.end():];Path('mut_'+sys.argv[1]+'.v').write_text(s)
PY
 iverilog -g2012 -s tb -o mut_${mut}.sim functional_cells_udp.v sram.v ovl_mapped.v mut_${mut}.v tb_ovl_active.sv > mut_${mut}.compile.log 2>&1
 if vvp mut_${mut}.sim > mut_${mut}.log 2>&1; then echo "BAD mutant accepted: $mut";exit 1;fi
 grep -q MISMATCH mut_${mut}.log
done
