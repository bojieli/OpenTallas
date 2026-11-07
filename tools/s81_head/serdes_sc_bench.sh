#!/usr/bin/env bash
# DIE-HEAD-76-SERDESRF: hd_serdes SC form lockstep bench (Verilator 5.050). usage (repo root cwd): serdes_sc_bench.sh OUTDIR
# production PASS (SC == RXQ, pma_tx +2) and every mutant FAIL; exit 0 iff all as expected.
set -u
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=${1:?outdir}; L=rtl/dsrom_sys/s81_link; T=rtl/dsrom_sys/s81_head; H=rtl/hbm_accel/cores_split/reform_1104b
M=physical/asap7_memory_macros; mkdir -p "$O"; rc=0
S=$T/ot_s81hd_serdes_sc.sv; C=$T/ot_s81hd_serdes_sc_cores.sv
one() { # name parent-file expected [cores-file]
  local n=$1 f=$2 e=$3 c=${4:-$C}; local d=$O/$n
  "$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style -Wno-UNOPTFLAT \
    -I$L -I$H --top-module tb_s81hd_serdes_sc_lockstep -Mdir "$d" \
    $T/ot_s81hd_serdes_link.sv $L/ot_pdie_serdes.sv $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $H/ot_s81_kp4_enc_la.sv \
    $L/ot_s81_kp4_dec.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dchn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dsyn.sv \
    $M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v $M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v \
    $T/ot_s81hd_serdes_rxq.sv "$c" "$f" $T/test/tb_s81hd_serdes_sc_lockstep.sv --build-jobs ${J:-4} > "$O/build_$n.log" 2>&1 \
    || { echo "$n BUILD FAIL"; grep -m5 %Error "$O/build_$n.log"; rc=1; return; }
  "$d/Vtb_s81hd_serdes_sc_lockstep" > "$O/run_$n.log" 2>&1
  r=$(grep -oE '^SERDES_SC (PASS|FAIL)' "$O/run_$n.log" | awk '{print $2}'); v=$([ "$r" = "$e" ] && echo OK || echo BAD); [ $v = OK ] || rc=1
  echo "$n expect=$e got=${r:-NONE} $v | $(grep -E '^(SC_STATS|SERDES_SC)' "$O/run_$n.log" | tr '\n' ' ' | cut -c1-320)"
}
edit() { python3 -I -c 'import sys
s,o,a,b=sys.argv[1:]; t=open(s).read(); assert t.count(a)==1,a; open(o,"w").write(t.replace(a,b))' "$@"; }
mut()  { edit "$S" "$O/$1.sv" "$2" "$3" && one "$1" "$O/$1.sv" FAIL; }        # parent mutant
mutc() { edit "$C" "$O/$1.sv" "$2" "$3" && one "$1" "$S" FAIL "$O/$1.sv"; }  # child mutant
one base "$S" PASS
mutc m_ldq ".ld(ldq), .S(S_b)" ".ld(ld_i), .S(S_b)"
mutc m_sb ".ld(ldq), .S(S_b)" ".ld(ldq), .S(S_i)"
mutc m_ff ".LA(2), .FF(1)" ".LA(2), .FF(0)"
mut m_bm1 ".ld_i(ldr[1])" ".ld_i(ldr[2])"
mut m_rm "else rm_l[gl] <= rm_r[gl / 6];" "else rm_l[gl] <= 1'b1;"
mut m_rml "if (!rrst_l[gs]) r_d[cb] <= (cb == 1);" "if (!rrst_l[gs]) r_d[cb] <= 1'b0;"
echo "SERDES_SC_BENCH rc=$rc"; exit $rc
