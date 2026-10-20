#!/bin/bash
# HBM-COLL6 10-20 (r2: + FANCOPY 2 = FC1 + kept m_vm copy for VM banks 4..7): v74k COLL protocol leaf (v74p MUL_PIPE 1 + FANCOPY 1: kept per-partial-product operand landings, hs_q x2)
# proofs on Verilator 5.050 (no added edge vs v74p; shift-equivalence vs v74 one edge earlier).
# usage: run_hbm_coll_fancopy_proofs_1020.sh OUT [TAG...]   (no TAG = all; runs in parallel, -j 2 each)
# PASS benches (must pass) and mutant benches (must FAIL with their fail regex): see the case table below.
#        run_hbm_coll_fancopy_proofs_1020.sh --raw OUT TAG   (one case, exit status = the bench's own: mutant benches)
set -uo pipefail
raw=0;if test "${1:-}" = --raw;then raw=1;shift;fi
out=${1:?output};shift;mkdir -p "$out";out=$(realpath "$out")
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
D=rtl/hbm_accel/generic/collective/p2p
S=("$D/ot_hfd_coll_q_hard_v5.sv" "$D/ot_hgi_coll_ctl_v5.sv" "$D/ot_hgi_coll_ctl_v5_safephys.sv" "$D/ot_hgi_coll_ctl_release_safephys.sv" "$D/ot_hgi_coll_fixed_delay_sram_safephys.sv" "$D/ot_hgi_coll_slice_v7.sv" rtl/hdc/ot_hdc_prefix.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir.v physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v)
verilator --version | tee "$out/verilator_version.txt"
# tag|top|expect|params
CASES=(
 "fast_s0|tb_hgi_coll_ctl_mulpipe_safephys|pass|-GSHAPE=0 -GFC=1 -GCARRY=1"
 "fast_s1|tb_hgi_coll_ctl_mulpipe_safephys|pass|-GSHAPE=1 -GFC=2 -GCARRY=1"
 "fast_s0_m4|tb_hgi_coll_ctl_mulpipe_safephys|fail|-GSHAPE=0 -GFC=1 -GMUT=4"
 "fast_s1_m2|tb_hgi_coll_ctl_mulpipe_safephys|fail|-GSHAPE=1 -GFC=2 -GMUT=2"
 "fast_s1_madd|tb_hgi_coll_ctl_mulpipe_safephys|fail|-GSHAPE=1 -GFC=2 +define+OT_COLL_FAST_MUT_ADD"
 "fast_s0_mfault|tb_hgi_coll_ctl_mulpipe_safephys|fail|-GSHAPE=0 -GFC=1 +define+OT_COLL_FAST_MUT_FAULT"
 "prod_s0|tb_hgi_coll_ctl_v74_safephys|pass|-GMULP=1 -GFC=1 -GSHAPE=0"
 "prod_s1|tb_hgi_coll_ctl_v74_safephys|pass|-GMULP=1 -GFC=2 -GSHAPE=1"
 "dense_s0|tb_hgi_coll_ctl_v74_safephys|pass|-GMULP=1 -GFC=1 -GSHAPE=0 -GDENSE=1"
 "dense_s1|tb_hgi_coll_ctl_v74_safephys|pass|-GMULP=1 -GFC=2 -GSHAPE=1 -GDENSE=1"

)
want=" $* "
if test $raw = 1;then
 for c in "${CASES[@]}";do
  IFS='|' read -r tag top expect params <<<"$c"
  if test "$top" != tb_hgi_coll_iter_safephys;then params="$params -GFAST16=1";fi
  test "$tag" = "${1:?tag}" || continue
  # shellcheck disable=SC2086
  verilator --binary --timing -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module "$top" --Mdir "$out/obj_$tag" -o tb $params "$D/$top.sv" "${S[@]}" > "$out/build_$tag.log" 2>&1 || { echo "BUILD_FAIL $tag";exit 3; }
  "$out/obj_$tag/tb" 2>&1 | tee "$out/$tag.log";exit "${PIPESTATUS[0]}"
 done
 echo "unknown tag $1";exit 2
fi
run(){
 local tag=$1 top=$2 expect=$3 params=$4
 # shellcheck disable=SC2086
 if ! verilator --binary --timing -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module "$top" --Mdir "$out/obj_$tag" -o tb $params "$D/$top.sv" "${S[@]}" > "$out/build_$tag.log" 2>&1;then
  grep -q "PCH\|pch" "$out/build_$tag.log" && verilator --binary --timing -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module "$top" --Mdir "$out/obj_$tag" -o tb $params "$D/$top.sv" "${S[@]}" > "$out/build_$tag.log" 2>&1 || { echo "RESULT $tag BUILD_FAIL";return 1; }
 fi
 if "$out/obj_$tag/tb" > "$out/$tag.log" 2>&1;then
  if test "$expect" = pass;then echo "RESULT $tag PASS $(grep -E 'PASS' "$out/$tag.log" | tail -1)";else echo "RESULT $tag MUTANT_SURVIVED";return 1;fi
 else
  if test "$expect" = fail;then echo "RESULT $tag MUTANT_FAILED_AS_EXPECTED $(grep -E 'FAIL' "$out/$tag.log" | tail -1)";else echo "RESULT $tag UNEXPECTED_FAIL";tail -8 "$out/$tag.log";return 1;fi
 fi
 rm -rf "$out/obj_$tag"
}
pids=()
for c in "${CASES[@]}";do
 IFS='|' read -r tag top expect params <<<"$c"
  if test "$top" != tb_hgi_coll_iter_safephys;then params="$params -GFAST16=1";fi
 if test "$want" != "  " && [[ "$want" != *" $tag "* ]];then continue;fi
 run "$tag" "$top" "$expect" "$params" > "$out/result_$tag.txt" 2>&1 &
 pids+=($!)
done
rc=0;for p in "${pids[@]}";do wait "$p" || rc=1;done
cat "$out"/result_*.txt | sort | tee "$out/summary.txt"
if test $rc = 0;then echo "COLL_FANCOPY_PROOFS PASS cases=${#pids[@]}";else echo "COLL_FANCOPY_PROOFS FAIL";fi
exit $rc
