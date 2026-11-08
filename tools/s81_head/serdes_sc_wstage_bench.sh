#!/usr/bin/env bash
# HEAD-FORMS-1: hd_serdes SC u_rm write stage (WSTAGE=1, +1 pma_rck). usage (repo root cwd): serdes_sc_wstage_bench.sh OUTDIR
# Positive: 3 clock phases and the rm release-skew-free reset epochs of the DH81-SEQ bench, dut beats in order vs RXQ; default-off stays exact.
# Mutants: wrong select, unstaged data, one slice never written, reader published 2 edges early. exit 0 iff all as expected.
set -u
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=${1:?outdir}; L=rtl/dsrom_sys/s81_link; T=rtl/dsrom_sys/s81_head; H=rtl/hbm_accel/cores_split/reform_1104b
M=physical/asap7_memory_macros; mkdir -p "$O"; rc=0
S=$T/ot_s81hd_serdes_sc.sv; W=$T/ot_s81hd_serdes_link_ls.sv
python3 -I - $L/ot_pdie_serdes_locksafe.sv "$O/hold_only.sv" <<'P' || exit 2
import re,sys
t=open(sys.argv[1]).read(); m=re.search(r"module ot_pdie_pma_reset_hold.*?endmodule", t, re.S)
open(sys.argv[2],"w").write("`timescale 1ns/1ps\n"+m.group(0)+"\n")
P
one() { # name expected sc-file verilator-params...
  local n=$1 e=$2 f=$3; shift 3; local d=$O/$n
  "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style -Wno-UNOPTFLAT \
    -DOT_S81HD_SERDES_SC -I$L -I$H --top-module tb_s81hd_serdes_sc_ls -Mdir "$d" "$@" \
    $T/ot_s81hd_serdes_link.sv "$W" "$O/hold_only.sv" $L/ot_pdie_serdes.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv \
    $H/ot_s81_kp4_enc_la.sv $L/ot_s81_kp4_dec.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dchn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dsyn.sv \
    $M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v \
    $T/ot_s81hd_serdes_rxq.sv $T/ot_s81hd_serdes_sc_cores.sv "$f" $T/test/tb_s81hd_serdes_sc_ls.sv --build-jobs ${J:-4} > "$O/build_$n.log" 2>&1 \
    || { echo "$n BUILD FAIL"; grep -m5 %Error "$O/build_$n.log"; rc=1; return; }
  "$d/Vtb_s81hd_serdes_sc_ls" > "$O/run_$n.log" 2>&1
  r=$(grep -m1 -oE "^SERDES_SC_LS (PASS|FAIL)" "$O/run_$n.log" | awk "{print \$2}"); v=$([ "$r" = "$e" ] && echo OK || echo BAD); [ $v = OK ] || rc=1
  echo "$n expect=$e got=${r:-NONE} $v | $(grep -m1 -E "^SERDES_SC_LS" "$O/run_$n.log" | cut -c1-220)"
}
edit() { python3 -I -c 'import sys
s,o,a,b=sys.argv[1:]; t=open(s).read(); assert t.count(a)==1,a; open(o,"w").write(t.replace(a,b))' "$@"; }
ON="-DOT_S81HD_SC_RM_WSTAGE -GRM_WSTAGE=1"
one off    PASS "$S"
one on     PASS "$S" $ON
one on137  PASS "$S" $ON -GPH=0.137
one on301  PASS "$S" $ON -GPH=0.301
edit "$S" "$O/m_sel.sv" "(8'd1 << wp[2:0]) : 8'd0;
            for (wk" "(8'd1 << (wp[2:0] + 3'd1)) : 8'd0;
            for (wk" && one m_sel FAIL "$O/m_sel.sv" $ON
edit "$S" "$O/m_data.sv" "<= wd_r[ws * 32 +: 32];" "<= w_d[ws * 32 +: 32];" && one m_data FAIL "$O/m_data.sv" $ON
edit "$S" "$O/m_slice.sv" "if (wsel[ws][wk]) mem" "if (wsel[ws][wk] && ws != 5) mem" && one m_slice FAIL "$O/m_slice.sv" $ON
edit "$S" "$O/m_off.sv" "if (WSTAGE == 0) mem[wp[2:0]] <= w_d;" "" && one m_nowrite_off FAIL "$O/m_off.sv"
echo "SERDES_SC_WSTAGE_BENCH rc=$rc"; exit $rc
