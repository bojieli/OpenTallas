#!/bin/bash
# S81.RESET adoption gates (DIE-S81-48 11-02).  Usage: run_gate.sh SRC ORIG_COMMIT_SRC OUT
#   SRC  = clean snapshot of the branch; ORIG = clean snapshot of the pre-change main (9db068b54); OUT = results dir.
# 1. the ba934c4af gate set unchanged (wrapper mechanism + native flat/col + 3 mutants) on the new sources;
# 2. in-core LOCKSAFE gate: default params == original core every edge, LOCKSAFE=1 == gated wrapper every edge,
#    release 66/68 after cold / warm-stopped / warm-running epochs; HOLD=63 and default-activation mutants must fail.
set -eu
S=$1; G=$2; O=$3
L=$S/rtl/dsrom_sys/s81_link
mkdir -p "$O"
# original core bodies, renamed *_orig (identity reference)
awk '/^module ot_pdie_serdes #/{p=1} p{print} p&&/^endmodule/{exit}' "$G/rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv" \
  | sed '1s/module ot_pdie_serdes #/module ot_pdie_serdes_orig #/' >"$O/orig_flat.sv"
awk '/^module ot_pdie_serdes_col #/{p=1} p{print} p&&/^endmodule/{exit}' "$G/rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv" \
  | sed '1s/module ot_pdie_serdes_col #/module ot_pdie_serdes_col_orig #/' >"$O/orig_col.sv"
grep -q "module ot_pdie_serdes_orig" "$O/orig_flat.sv"; grep -q "module ot_pdie_serdes_col_orig" "$O/orig_col.sv"
small=("$L/ot_pdie_serdes.sv" "$L/ot_pdie_serdes_locksafe.sv" "$L/tb_pdie_locksafe_reset.sv")
for C in base early ignorelock; do
 args=()
 case $C in early)args=(-Ptb_pdie_locksafe_reset.HOLD=63);;ignorelock)args=(-Ptb_pdie_locksafe_reset.IGNORE_LOCK=1);;esac
 iverilog -g2012 -s tb_pdie_locksafe_reset "${args[@]}" -o "$O/$C" "${small[@]}" >"$O/$C.build.log" 2>&1
 set +e;vvp "$O/$C" >"$O/$C.log" 2>&1;rc=$?;set -e
 echo "$rc" >"$O/$C.rc"
 if [ "$C" = base ];then test "$rc" = 0;else test "$rc" != 0;grep -q -E 'early release|unsafe FIFO' "$O/$C.log";fi
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
for C in inflat incol inearly indefault;do
 args=()
 case $C in incol)args=(-Ptb_pdie_locksafe_incore.COL=1);;inearly)args=(-Ptb_pdie_locksafe_incore.COL=1 -Ptb_pdie_locksafe_incore.HOLD=63);;indefault)args=(-Ptb_pdie_locksafe_incore.DEFAULT_MUT=1);;esac
 iverilog -g2012 -I "$L" -s tb_pdie_locksafe_incore "${args[@]}" -o "$O/$C" "${files[@]}" "$O/orig_flat.sv" "$O/orig_col.sv" "$L/tb_pdie_locksafe_incore.sv" >"$O/$C.build.log" 2>&1
 set +e;vvp "$O/$C" >"$O/$C.log" 2>&1;rc=$?;set -e
 echo "$rc" >"$O/$C.rc"
 case $C in inearly)test "$rc" != 0;grep -q -E 'early release' "$O/$C.log";;indefault)test "$rc" != 0;grep -q 'default core differs' "$O/$C.log";;*)test "$rc" = 0;grep -q 'LOCKSAFE_INCORE PASS' "$O/$C.log";;esac
 echo "GATE $C rc=$rc OK"
done
echo LOCKSAFE_ADOPT_GATE_PASS | tee "$O/verdict.txt"
