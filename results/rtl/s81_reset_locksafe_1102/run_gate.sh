#!/bin/bash
# S81.RESET adoption gates (DIE-S81-49 11-02, OWNER 17:55 SerDes warm-reset sequencer).  Usage: run_gate.sh SRC ORIG OUT
#   SRC  = clean snapshot of this branch; ORIG = clean snapshot of its base main (released ot_pdie_serdes_col); OUT = results.
# 1. the codex/serdes-locksafe-2047 (ba934c4af) gate set on the new sources: shared ot_pdie_pma_reset_hold + real FIFO
#    (cold / stopped / warm / relock, HOLD63 + IGNORE_LOCK mutants) and the native flat/col wrappers (+ default mutant);
# 2. S81 in-column gate tb_s81_col_locksafe: default column == released column every edge; LOCKSAFE=1 column == shared
#    gated wrapper every edge; release rck 66/68 after 5 epochs; HOLD63 / IGNORE_LOCK / DEFAULT_MUT mutants must fail.
set -eu
S=$1; G=$2; O=$3
L=$S/rtl/dsrom_sys/s81_link
mkdir -p "$O"
awk '/^module ot_pdie_serdes_col #/{p=1} p{print} p&&/^endmodule/{exit}' "$G/rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv" \
  | sed '1s/module ot_pdie_serdes_col #/module ot_pdie_serdes_col_orig #/' >"$O/orig_col.sv"
grep -q "module ot_pdie_serdes_col_orig" "$O/orig_col.sv"
small=("$L/ot_pdie_serdes.sv" "$L/ot_pdie_serdes_locksafe.sv" "$L/tb_pdie_locksafe_reset.sv")
for C in base early ignorelock; do
 args=()
 case $C in early)args=(-Ptb_pdie_locksafe_reset.HOLD=63);;ignorelock)args=(-Ptb_pdie_locksafe_reset.IGNORE_LOCK=1);;esac
 iverilog -g2012 -s tb_pdie_locksafe_reset "${args[@]}" -o "$O/$C" "${small[@]}" >"$O/$C.build.log" 2>&1
 set +e;vvp "$O/$C" >"$O/$C.log" 2>&1;rc=$?;set -e
 echo "$rc" >"$O/$C.rc"
 if [ "$C" = base ];then test "$rc" = 0;grep -q 'LOCKSAFE_RESET PASS' "$O/$C.log";else test "$rc" != 0;grep -q -E 'early release|unsafe FIFO' "$O/$C.log";fi
 echo "GATE $C rc=$rc OK"
done
files=("$L/ot_s81_kp4_common.sv" "$L/ot_s81_kp4_enc.sv" "$L/ot_s81_kp4_bm.sv" "$L/ot_s81_kp4_dsyn.sv" "$L/ot_s81_kp4_ddly.sv" "$L/ot_s81_kp4_dchn.sv" "$L/ot_s81_kp4_dout.sv" "$L/ot_s81_kp4_dec.sv" "$S/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" "$S/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v" "$S/rtl/common/landed_parent/ot_pl_land.sv" "$L/lp/ot_s81_kp4_dec_native_flat_lp.sv" "$L/col/ot_pdie_serdes_col.sv" "$L/ot_pdie_serdes.sv" "$L/ot_pdie_serdes_locksafe.sv")
for C in flat col defaultmut;do
 args=()
 case $C in col)args=(-Ptb_pdie_locksafe_native.COL=1);;defaultmut)args=(-Ptb_pdie_locksafe_native.DEFAULT_MUT=1);;esac
 iverilog -g2012 -I "$L" -s tb_pdie_locksafe_native "${args[@]}" -o "$O/$C" "${files[@]}" "$L/tb_pdie_locksafe_native.sv" >"$O/$C.build.log" 2>&1
 set +e;vvp "$O/$C" >"$O/$C.log" 2>&1;rc=$?;set -e
 echo "$rc" >"$O/$C.rc"
 if [ "$C" = defaultmut ];then test "$rc" != 0;grep -q 'default wrapper differs' "$O/$C.log";else test "$rc" = 0;fi
 echo "GATE $C rc=$rc OK"
done
for C in s81col s81early s81nolock s81default;do
 args=()
 case $C in s81early)args=(-Ptb_s81_col_locksafe.HOLD=63);;s81nolock)args=(-Ptb_s81_col_locksafe.IGNORE_LOCK=1);;s81default)args=(-Ptb_s81_col_locksafe.DEFAULT_MUT=1);;esac
 iverilog -g2012 -I "$L" -s tb_s81_col_locksafe "${args[@]}" -o "$O/$C" "${files[@]}" "$O/orig_col.sv" "$L/col/tb_s81_col_locksafe.sv" >"$O/$C.build.log" 2>&1
 set +e;vvp "$O/$C" >"$O/$C.log" 2>&1;rc=$?;set -e
 echo "$rc" >"$O/$C.rc"
 case $C in
  s81col)test "$rc" = 0;grep -q 'S81_COL_LOCKSAFE PASS' "$O/$C.log";test "$(grep -c S81_COL_RELEASE "$O/$C.log")" = 5;;
  s81early)test "$rc" != 0;grep -q 'early release' "$O/$C.log";;
  s81nolock)test "$rc" != 0;grep -q -E 'not held|differs from gated' "$O/$C.log";;
  s81default)test "$rc" != 0;grep -q 'default column differs' "$O/$C.log";;
 esac
 echo "GATE $C rc=$rc OK"
done
echo S81_LOCKSAFE_ADOPT_GATE_PASS | tee "$O/verdict.txt"
