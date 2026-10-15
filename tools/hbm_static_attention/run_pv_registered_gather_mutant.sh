#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
python3 - "$out/mutant.sv" <<'PY'
import sys
from pathlib import Path
s=Path('rtl/hdc/v41x/static/ot_hbm_attn_pv_group_gather_registered.sv').read_text()
a='select_q<=block_select;';b="select_q<=block_select^3'b001;"
assert s.count(a)==1
Path(sys.argv[1]).write_text(s.replace(a,b))
PY
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_attn_pv_serializer_local_registered --Mdir "$out/obj" -o sim \
 rtl/hdc/v41x/static/ot_hbm_attn_pv_serializer_local.sv "$out/mutant.sv" rtl/hdc/v41x/static/ot_hbm_attn_pv_serializer_local_registered.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 rtl/test/hbm_accel/generic/tb_hbm_attn_pv_serializer_local_registered.sv > "$out/build.log" 2>&1
set +e;"$out/obj/sim" +MUT=0 +OVERLAP=1 > "$out/mutant.log" 2>&1;rc=$?;set -e;echo "$rc" > "$out/mutant.rc"
if [ "$rc" = 0 ];then echo 'FAIL registered DUT blockselector mutant survived';exit 1;fi
grep -q 'PV_LOCAL_SERIALIZER data mismatch' "$out/mutant.log"
echo 'PASS actual registeredgather DUT blockselector mutant rejected' > "$out/gate"
