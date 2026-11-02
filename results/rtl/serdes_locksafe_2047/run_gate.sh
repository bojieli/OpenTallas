#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/codex-serdes-locksafe-2047
S=$R/src
L=$S/rtl/dsrom_sys/s81_link
O=$R/results
mkdir -p "$O"
small=("$L/ot_pdie_serdes.sv" "$L/ot_pdie_serdes_locksafe.sv" "$L/tb_pdie_locksafe_reset.sv")
for C in base early ignorelock; do
 args=()
 case $C in early)args=(-Ptb_pdie_locksafe_reset.HOLD=63);;ignorelock)args=(-Ptb_pdie_locksafe_reset.IGNORE_LOCK=1);;esac
 iverilog -g2012 -s tb_pdie_locksafe_reset "${args[@]}" -o "$O/$C" "${small[@]}" >"$O/$C.build.log" 2>&1
 set +e;vvp "$O/$C" >"$O/$C.log" 2>&1;rc=$?;set -e
 echo "$rc" >"$O/$C.rc"
 if [ "$C" = base ];then test "$rc" = 0;else test "$rc" != 0;grep -q -E 'early release|unsafe FIFO' "$O/$C.log";fi
 done
files=("$L/ot_s81_kp4_common.sv" "$L/ot_s81_kp4_enc.sv" "$L/ot_s81_kp4_bm.sv" "$L/ot_s81_kp4_dsyn.sv" "$L/ot_s81_kp4_ddly.sv" "$L/ot_s81_kp4_dchn.sv" "$L/ot_s81_kp4_dout.sv" "$L/ot_s81_kp4_dec.sv" "$S/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" "$S/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v" "$S/rtl/common/landed_parent/ot_pl_land.sv" "$L/lp/ot_s81_kp4_dec_native_flat_lp.sv" "$L/col/ot_pdie_serdes_col.sv" "$L/ot_pdie_serdes.sv" "$L/ot_pdie_serdes_locksafe.sv" "$L/tb_pdie_locksafe_native.sv")
for C in flat col defaultmut;do
 args=()
 case $C in col)args=(-Ptb_pdie_locksafe_native.COL=1);;defaultmut)args=(-Ptb_pdie_locksafe_native.DEFAULT_MUT=1);;esac
 iverilog -g2012 -I "$L" -s tb_pdie_locksafe_native "${args[@]}" -o "$O/$C" "${files[@]}" >"$O/$C.build.log" 2>&1
 set +e;vvp "$O/$C" >"$O/$C.log" 2>&1;rc=$?;set -e
 echo "$rc" >"$O/$C.rc"
 if [ "$C" = defaultmut ];then test "$rc" != 0;grep -q 'default wrapper differs' "$O/$C.log";else test "$rc" = 0;fi
 done
echo LOCKSAFE_GATE_PASS | tee "$O/verdict.txt"
