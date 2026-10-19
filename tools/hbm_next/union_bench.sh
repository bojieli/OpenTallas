#!/bin/bash
# Fleet only; Verilator matches closure daemon 5.050. Always verify expected fail text and exit status.
set -eu
O=$(realpath -m "${1:-union_out}");mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$O/verilator.txt"
SRC=(rtl/hbm_next/control/ot_hnx_union_calendar.sv rtl/hbm_next/control/tb_hnx_union_calendar.sv)
for m in 0 1; do
 verilator --binary --timing -j 2 -Wno-fatal --top-module tb_hnx_union_calendar -GMUT=$m -Mdir "$O/calobj$m" "${SRC[@]}" > "$O/cal_build$m.log" 2>&1
 set +e; "$O/calobj$m/Vtb_hnx_union_calendar" > "$O/cal_run$m.log" 2>&1; rc=$?;set -e
 if [ "$m" = 0 ];then [ "$rc" = 0 ];grep -q 'UNION_CALENDAR PASS' "$O/cal_run$m.log"
 else [ "$rc" != 0 ];grep -q 'UNION_WRONG_VARIANT' "$O/cal_run$m.log";fi
 echo "calendar m$m expected exit=$rc"
done
VS=rtl/hbm_accel/generic/vm/static
SRC=(rtl/hbm_next/idx/ot_hnx_idx_union_static.sv rtl/hbm_next/control/ot_hnx_union_calendar.sv
 rtl/hbm_next/control/tb_hnx_union_boundary.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv
 $VS/hfd_hgi_vms_static.sv $VS/ot_vms_slice_static.sv $VS/ot_vms_hub_static.sv $VS/ot_vms_bank_static.sv
 $VS/ot_vms_rstop_static.sv $VS/ot_vms_rcl_static.sv $VS/ot_vms_status_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
sha256sum "${SRC[@]}" > "$O/boundary_sources.sha256"
python3 tools/hbm_next/union_boundary_vectors.py "$O/boundary_vectors" 1019 0 > "$O/vector.log"
python3 - "$O/boundary_vectors" <<'PY2'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); rows=json.loads((p/'rows.json').read_text());exp=[0]*16384
for r in rows:
 if not r['fault']:exp[r['G']+r['edges']-1]=r['U']
(p/'u_expect.mem').write_text(''.join(f'{x:03x}\n' for x in exp))
PY2
for m in 0 1;do
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hnx_union_boundary -GCMUT=$m -Mdir "$O/boundobj$m" "${SRC[@]}" > "$O/bound_build$m.log" 2>&1
 set +e;(cd "$O/boundary_vectors"; "$O/boundobj$m/Vtb_hnx_union_boundary") > "$O/bound_run$m.log" 2>&1;rc=$?;set -e
 if [ "$m" = 0 ];then [ "$rc" = 0 ];grep -q 'UNION_BOUNDARY PASS' "$O/bound_run$m.log"
 else [ "$rc" != 0 ];grep -q 'UNION_BOUNDARY_WRONG_VARIANT' "$O/bound_run$m.log";fi
 echo "real IDX boundary m$m expected exit=$rc"
done
