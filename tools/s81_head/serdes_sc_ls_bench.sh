#!/usr/bin/env bash
# DH81-SEQ: warm-reset sequencer on the hd_serdes SC form (Verilator 5.050). usage (repo root cwd): serdes_sc_ls_bench.sh OUTDIR
# Production (3 clock phases) PASS, one rm tree release-skew control PASS, every mutant FAIL; exit 0 iff all as expected.
set -u
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=${1:?outdir}; L=rtl/dsrom_sys/s81_link; T=rtl/dsrom_sys/s81_head; H=rtl/hbm_accel/cores_split/reform_1104b
M=physical/asap7_memory_macros; mkdir -p "$O"; rc=0
S=$T/ot_s81hd_serdes_sc.sv; W=$T/ot_s81hd_serdes_link_ls.sv
# the shared file also holds wrappers around other cores: the bench compiles exactly the sequencer module from it
python3 -I - $L/ot_pdie_serdes_locksafe.sv "$O/hold_only.sv" <<'P' || exit 2
import re,sys
t=open(sys.argv[1]).read(); m=re.search(r"module ot_pdie_pma_reset_hold.*?endmodule", t, re.S)
open(sys.argv[2],"w").write("`timescale 1ns/1ps\n"+m.group(0)+"\n")
P
one() { # name expected sc-file wrapper-file verilator-params...
  local n=$1 e=$2 f=$3 w=$4; shift 4; local d=$O/$n
  "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style -Wno-UNOPTFLAT \
    -DOT_S81HD_SERDES_SC -I$L -I$H --top-module tb_s81hd_serdes_sc_ls -Mdir "$d" "$@" \
    $T/ot_s81hd_serdes_link.sv "$w" "$O/hold_only.sv" $L/ot_pdie_serdes.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv \
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
one base  PASS "$S" "$W"
one ph137 PASS "$S" "$W" -GPH=0.137
one ph301 PASS "$S" "$W" -GPH=0.301
# control: core_rst_n is no longer ck-synchronous, so in silicon the rm_r copies may split by one ck edge. Odd leaves one edge late must be invisible.
edit "$S" "$O/skew1.sv" "else rm_l[gl] <= rm_r[gl / 6];" "else rm_l[gl] <= (gl % 2) ? rm_x[gl / 6] : rm_r[gl / 6];" && \
  edit "$O/skew1.sv" "$O/skew2.sv" "if (!rst) rm_r <= 3'b000; else rm_r <= 3'b111;" \
  "if (!rst) rm_r <= 3'b000; else rm_r <= 3'b111; reg [2:0] rm_x; always @(posedge clk or negedge rst) if (!rst) rm_x <= 3'b000; else rm_x <= rm_r;" && \
  one skew_rm PASS "$O/skew2.sv" "$W"
one m_hold61 FAIL "$S" "$W" -GHOLD=61
one m_lock   FAIL "$S" "$W" -GIGNORE_LOCK=1
edit "$S" "$O/m_chn.sv" "ot_s81_kp4_dchn u_chn (.clk(clk), .rst_n(rst_n)," "ot_s81_kp4_dchn u_chn (.clk(clk), .rst_n(1'b1)," && one m_chn FAIL "$O/m_chn.sv" "$W"
edit "$S" "$O/m_tx.sv" "ot_s81hd_sc_tx u_tx (.clk(clk), .rst(rst)," "ot_s81hd_sc_tx u_tx (.clk(clk), .rst(1'b1)," && one m_tx FAIL "$O/m_tx.sv" "$W"
python3 -I - "$W" "$O/m_wrap.sv" <<'P' && one m_wrap_raw FAIL "$S" "$O/m_wrap.sv"
import sys
s=open(sys.argv[1]).read(); a="ot_s81hd_pdie_sc #(.PMA_LAT(PMA_LAT)) u_link (\n        .clk(ck), .rst(core_rst_n),"; assert s.count(a)==1
open(sys.argv[2],"w").write(s.replace(a,a.replace("core_rst_n","rst_n")))
P
echo "SERDES_SC_LS_BENCH rc=$rc"; exit $rc
