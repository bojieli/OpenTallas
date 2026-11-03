#!/bin/bash
# HEAD warm-reset sequencer gate (DIE-HEAD-54). Usage: run_gate.sh REPO_ROOT OUT_DIR
set -eu
S=$1; O=$2; L=$S/rtl/dsrom_sys/s81_link; H=$S/rtl/dsrom_sys/s81_head
mkdir -p "$O"
files=("$L/ot_s81_kp4_common.sv" "$L/ot_s81_kp4_enc.sv" "$L/ot_s81_kp4_bm.sv" "$L/ot_s81_kp4_dsyn.sv" "$L/ot_s81_kp4_ddly.sv" "$L/ot_s81_kp4_dchn.sv" "$L/ot_s81_kp4_dout.sv" "$L/ot_s81_kp4_dec.sv" "$S/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" "$S/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v" "$L/ot_pdie_serdes.sv" "$L/ot_pdie_serdes_locksafe.sv" "$H/ot_s81hd_serdes_link.sv" "$H/ot_s81hd_serdes_link_ls.sv" "$H/tb_s81hd_serdes_link_ls.sv")
for C in base hold63 ignorelock dmut; do
 args=()
 case $C in hold63)args=(-Ptb_s81hd_serdes_link_ls.HOLD=63);;ignorelock)args=(-Ptb_s81hd_serdes_link_ls.IGNORE_LOCK=1);;dmut)args=(-Ptb_s81hd_serdes_link_ls.DMUT=1);;esac
 iverilog -g2012 -I "$L" -s tb_s81hd_serdes_link_ls "${args[@]}" -o "$O/$C" "${files[@]}" >"$O/$C.build.log" 2>&1
 set +e; vvp "$O/$C" >"$O/$C.log" 2>&1; rc=$?; set -e
 echo "$rc" >"$O/$C.rc"; rm -f "$O/$C"
 case $C in
  base) test "$rc" = 0; grep -q 'HEAD_LOCKSAFE PASS' "$O/$C.log";;
  hold63) test "$rc" != 0; grep -q -E 'early release|differs' "$O/$C.log";;
  ignorelock) test "$rc" != 0; grep -q -E 'differs|unsafe' "$O/$C.log";;
  dmut) test "$rc" != 0; grep -q 'default wrapper differs' "$O/$C.log";;
 esac
 echo "$C rc=$rc OK"
done
echo HEAD_LOCKSAFE_GATE_PASS | tee "$O/verdict.txt"
