#!/usr/bin/env bash
# DIE-HEAD-66: hd_serdes RXQ bench. usage (repo root cwd): rxq_bench.sh OUTDIR. production PASS, mutants FAIL, plus the rate_match slip bench on RXQ.
set -u
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=${1:?outdir}; L=rtl/dsrom_sys/s81_link; T=rtl/dsrom_sys/s81_head; mkdir -p "$O"; rc=0
TB=${TB:-$T/test/tb_s81hd_serdes_rxq.sv}
M=physical/asap7_memory_macros
one() { # name file-with-mutation expected
  local n=$1 f=$2 e=$3; local d=$O/$n
  "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style -Wno-UNOPTFLAT -I$L --top-module tb_s81hd_serdes_rxq -Mdir "$d" \
    $L/ot_pdie_serdes.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_dec.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dchn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dsyn.sv \
    $M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v "$f" "$TB" --build-jobs ${J:-4} > "$O/build_$n.log" 2>&1 \
    || { echo "$n BUILD FAIL"; grep -m5 %Error "$O/build_$n.log"; rc=1; return; }
  "$d/Vtb_s81hd_serdes_rxq" > "$O/run_$n.log" 2>&1
  r=$(grep -oE '^SERDES_RXQ (PASS|FAIL)' "$O/run_$n.log" | awk '{print $2}'); v=$([ "$r" = "$e" ] && echo OK || echo BAD); [ $v = OK ] || rc=1
  echo "$n expect=$e got=${r:-NONE} $v | $(grep -E '^(RXQ_STATS|SERDES_RXQ)' "$O/run_$n.log" | tr '\n' ' ' | cut -c1-300)"
}
S=$T/ot_s81hd_serdes_rxq.sv
one base "$S" PASS
mut() { n=$1; a=$2; b=$3; python3 -I - "$S" "$O/$n.sv" "$a" "$b" <<'PY'
import sys
s,o,a,b=sys.argv[1:]; t=open(s).read(); assert t.count(a)==1,a; open(o,'w').write(t.replace(a,b))
PY
  one "$n" "$O/$n.sv" FAIL; }
mut m_dd "DD(55 + 2)" "DD(55 + 1)"
mut m_ld ".ld(ldq[gu])" ".ld(ldr[gu])"
mut m_s ".S(S_b[gu])" ".S(S_q)"
mut m_am "(sum01[1] & n2[0])" "1'b0"
mut m_kv "assign k_v  = k_v_r;" "assign k_v  = cl;"
mut m_nb "nb[2] = (x == 4'b0011) |" "nb[2] ="
mut m_rsel "(8'd1 << rp[2:0])" "(8'd1 << (rp[2:0] + 3'd1))"
mut m_idl "((cb == 1) & ridl) |" ""
# rate match slip, both directions, RXQ renamed to the bench's DUT name
for f in 1 0; do
  python3 -I - "$S" "$O/rm.sv" <<'PY'
import re,sys
t=open(sys.argv[1]).read(); m=re.search(r'^module ot_s81hd_rate_match_q.*?^endmodule',t,re.S|re.M).group(0)
open(sys.argv[2],'w').write('`timescale 1ns/1ps\n'+m.replace('ot_s81hd_rate_match_q','ot_s81_rate_match'))
PY
  iverilog -g2012 -s tb_s81_rate_match -P tb_s81_rate_match.FAST=$f -o "$O/rm$f.vvp" $L/tb_s81_rate_match.sv "$O/rm.sv" > "$O/rm_b$f.log" 2>&1 || { echo RM_BUILD_FAIL; rc=1; }
  vvp -n "$O/rm$f.vvp" > "$O/rm_r$f.log" 2>&1; echo "rate_match FAST=$f: $(tail -1 "$O/rm_r$f.log" | cut -c1-200)"; grep -qiE "fail|error" "$O/rm_r$f.log" && rc=1
done
echo "RXQ_BENCH rc=$rc"; exit $rc
