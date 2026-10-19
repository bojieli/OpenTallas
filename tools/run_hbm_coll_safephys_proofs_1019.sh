#!/bin/bash
set -euo pipefail
out=${1:?output};mkdir -p "$out";out=$(realpath "$out")
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
D=rtl/hbm_accel/generic/collective/p2p
S=("$D/ot_hfd_coll_q_hard_v5.sv" "$D/ot_hgi_coll_ctl_v5.sv" "$D/ot_hgi_coll_ctl_v5_safephys.sv" "$D/ot_hgi_coll_ctl_release_safephys.sv" "$D/ot_hgi_coll_fixed_delay_sram_safephys.sv" "$D/ot_hgi_coll_slice_v7.sv" rtl/hdc/ot_hdc_prefix.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir.v physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v)
verilator --version
run(){
 local tag=$1 top=$2 expect=$3;shift 3
 verilator --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module "$top" --Mdir "$out/obj_$tag" -o tb "$@" "$D/$top.sv" "${S[@]}" > "$out/build_$tag.log" 2>&1
 if "$out/obj_$tag/tb" > "$out/$tag.log" 2>&1;then
  test "$expect" = pass || { echo "MUTANT_SURVIVED $tag";exit 1; }
  grep -E 'PASS|COLL_VMRT' "$out/$tag.log" | tail -2
 else
  test "$expect" = fail || { tail -12 "$out/$tag.log";exit 1; }
  grep -E 'FAIL|Error|Fatal' "$out/$tag.log" | tail -2
 fi
}
for m in 0 1 2;do ex=fail;test "$m" != 0 || ex=pass;run iter$m tb_hgi_coll_iter_safephys $ex -GMUT=$m;done
for m in 0 1 2 3 4;do ex=fail;test "$m" != 0 || ex=pass;run mech$m tb_hgi_coll_fixed_delay_sram_safephys $ex -GMUT=$m;done
for s in 0 1;do
 for m in 0 1 2 3;do ex=fail;test "$m" != 0 || ex=pass;run s${s}m${m} tb_hgi_coll_ctl_v74_safephys $ex -GSHAPE=$s -GMUT=$m;done
 run s${s}dense tb_hgi_coll_ctl_v74_safephys pass -GSHAPE=$s -GDENSE=1
done
