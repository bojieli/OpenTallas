#!/bin/bash
# Remote admitted execution only. Exact repeated command component, no full-die simulation.
set -euo pipefail
O=$(readlink -m "$1");mkdir -p "$O/fx"
python3 - "$O/fx" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,'tools')
import ha2_ar_fixture as HF
import numpy as np, hdc_golden as G
original_build=HF.build
def canonical_build(shape,seed):
    s,parts,z=original_build(shape,seed)
    if s['NC']==1: parts[:,0:8]=np.float32(-0.0)
    if s['NC']==1:
        # U2: physical NC8 tree pads inactive operands with +0; signed zero canonicalizes.
        z=G.to_bf16(G.add(parts,np.zeros_like(parts)))
    return s,parts,z
HF.build=canonical_build
for c,(n,pf) in enumerate(((1,8),(2,16),(4,16),(8,32),(8,64))):
    name=f'rearm{c}'
    HF.SHAPES[name]=dict(GS=n,NG=96//n,NC=n,NOG=96//n,E=pf*16,LANES=16,ONESHOT=0,BF16=1)
    HF.write(Path(sys.argv[1])/f'c{c}',name,20261009+c)
PY
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
SRC="rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $M rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv rtl/hbm_accel/tu/tb_hgi_coll_rearm.sv"
for mode in ${MODES:-positive premature_done};do
 D=();[ "$mode" = premature_done ] && D=(+define+OT_COLL_MUT_PREMATURE_DONE)
 "$V" --binary --timing -j 4 -Wno-fatal --top-module tb_hgi_coll_rearm --Mdir "$O/$mode" +define+TU_PCLK_IS_CLK +define+TU_SYNCPHY "${D[@]}" $SRC > "$O/build_$mode.log" 2>&1
 set +e; "$O/$mode/Vtb_hgi_coll_rearm" +VEC="$O/fx" > "$O/$mode.log" 2>&1;rc=$?;set -e
 if [ "$mode" = positive ];then [ "$rc" = 0 ];grep -q 'REARM PASS commands=45' "$O/$mode.log";else [ "$rc" != 0 ];grep -q PREMATURE_DONE "$O/$mode.log";fi
 echo "$mode rc=$rc" >> "$O/verdict.txt"
 if [ "$mode" = positive ];then
   "$O/positive/Vtb_hgi_coll_rearm" +VEC="$O/fx" +DUPLICATE_LAST=1 > "$O/duplicate.log" 2>&1
   grep -q 'REARM_DUPLICATE PASS' "$O/duplicate.log"
   ! grep -q '%Fatal' "$O/duplicate.log"
 fi
done
echo 'CX_COLL_REARM PASS' >> "$O/verdict.txt"
