#!/bin/bash
# HBM-NEXT-UNITS 2026-10-19: hnx HC N-row benches (fleet, Verilator 5.050).  Run from a bundle root (git archive of the
# lane branch) on a fleet host:  tools/hbm_next/hnx_hc_bench.sh OUT
#  1. hc_q row-stride unit bench (tb_hnx_hc_q, real lg pair leaves + split tap + fixed-latency VM model):
#       q_n4s   SPR 80, N 4, residual stride 1024, result stride 64     -> TB_HNX_HC_Q PASS
#       q_d4g   SPR 320, N 2, strides 0 (= the d4g bench exactly)        -> TB_HNX_HC_Q PASS
#       q_m7    q_n4s with MUT 7 (reader ignores the row stride)         -> TB_HNX_HC_Q FAIL (fail witness)
#       q_m8    q_n4s with MUT 8 (store ignores the row stride)          -> TB_HNX_HC_Q FAIL (fail witness)
#       q_m9    q_n4s with MUT 9 (HUBFIX: E face copy of the beat-control register one edge late) -> FAIL (fail witness)
#  2. HC_MIX N-row throughput + lockstep (tb_hnx_hc_eng4: ot_hnx_hc_root TPRE 6 + 4 x ot_hnx_hc_qeng ring = qcen + 8
#     bankq tiles, the d4g U-ring form DRLY 2 / XRLY 1 / QDRLY 2, RAW0 167 / RS 104), golden = hdc_golden_v41 chunk8
#     mixes + the codex tail reference (tools/rtl_hbm_hc_eng_static_gate.py --split):
#       e0 MUT 0: N = 1,2,3,4,6,8 -> HC_ENG PASS each; HC_MIX_CYCLES(N) -> further-row II
#       e4 MUT 4 (quarter-0 tree pairs (0,2),(1,3)), N 4 -> HC_ENG FAIL (fail witness)
#       e1 MUT 1 (quarter-0 bank-3 rotation), N 4      -> HC_ENG FAIL (fail witness)
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); ST=${2:?STAGE}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict_$ST.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null)"
H=rtl/hbm_next/hc
COMMON=(rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv)
QSRC=(rtl/hbm_next/hc/tb/tb_hnx_hc_q.sv $H/ot_hnx_hc_q.sv $H/ot_hnx_hgi_hc_residual_vm.sv $H/ot_hnx_hgi_hc_result_vm.sv
  $H/ot_hnx_hgi_hc_gathered_mix_reader.sv $H/ot_hnx_hc_xw_rx.sv $H/ot_hnx_hc_xbrep.sv rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv
  rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_split_term.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank_term.sv
  rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv "${COMMON[@]}"
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
qbuild(){ # tag "-G..."
  local d=$O/obj_$1; rm -rf $d
  verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hnx_hc_q $2 -Mdir $d -o V$1 \
    "${QSRC[@]}" > $O/build_$1.log 2>&1 || { sleep 5; verilator --binary --timing -j 1 -Wno-fatal -Wno-lint -Wno-style \
    --top-module tb_hnx_hc_q $2 -Mdir $d -o V$1 "${QSRC[@]}" > $O/build_$1.log 2>&1; }
  ( cd $O && $d/V$1 > $O/$1.log 2>&1; echo RUN_RC=$? >> $O/$1.log )
  V "$1: $(grep -h 'TB_HNX_HC_Q' $O/$1.log | head -1)"; rm -rf $d
}
ESRC=(rtl/hbm_next/hc/tb/tb_hnx_hc_eng4.sv $H/ot_hnx_hc_root.sv $H/ot_hnx_hc_qeng.sv $H/ot_hnx_hc_qcen.sv $H/ot_hnx_hc_bankq.sv
  $H/ot_hnx_hc_eng_seq.sv $H/ot_hnx_hc_bank.sv $H/ot_hnx_hc_tail_unit.sv $H/ot_hnx_hcp_sys1.sv $H/ot_hnx_hgi_hc_tail.sv
  $H/ot_hnx_hc_xw_rx.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv
  rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv
  rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv
  rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv "${COMMON[@]}"
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
NS="-GSPR=80 -GRNPOS=4 -GRSTRIDE=1024 -GSSTRIDE=64"
if [ "$ST" = q ]; then
  qbuild q_n4s "$NS -GMUT=0" & qbuild q_d4g "-GSPR=320 -GRNPOS=2 -GRSTRIDE=0 -GSSTRIDE=0 -GMUT=0" &
  qbuild q_m7 "$NS -GMUT=7" & qbuild q_m8 "$NS -GMUT=8" & qbuild q_m9 "$NS -GMUT=9" &
  wait
  # lint of the eng4 lockstep sources (catches elaboration errors before the 50 GB hierarchical builds)
  verilator --lint-only --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hnx_hc_eng4 \
    +define+MUT=0 +define+OT_FP_DATA_NORST +define+HC_DRLY=2 +define+HC_XRLY=1 +define+HC_QDRLY=2 "${ESRC[@]}" > $O/lint_eng4.log 2>&1
  V "lint eng4 rc=$? errors=$(grep -c '%Error' $O/lint_eng4.log)"
  V "done"; exit 0
fi
case $ST in
  q0) qbuild q_n4s "$NS -GMUT=0" & qbuild q_d4g "-GSPR=320 -GRNPOS=2 -GRSTRIDE=0 -GSSTRIDE=0 -GMUT=0" & wait
      np=$(grep -h '^TB_HNX_HC_Q PASS MUT=0' $O/q_n4s.log $O/q_d4g.log | wc -l)
      [ "$np" = 2 ] && V "HNX_HC_Q_BENCH PASS 2/2" || V "HNX_HC_Q_BENCH FAIL $np/2"; exit 0;;
  qm7) qbuild q_m7 "$NS -GMUT=7"; exit 0;;
  qm8) qbuild q_m8 "$NS -GMUT=8"; exit 0;;
  qm9) qbuild q_m9 "$NS -GMUT=9"; exit 0;;
esac
# ---- HC_MIX N-row cases
case $ST in e0) NL="1 2 3 4 6 8";; *) NL="4";; esac
for n in $NL; do python3 tools/rtl_hbm_hc_eng_static_gate.py --run $O/cases_$ST/n$n --split --npos $n --raw0 167 --rs 104 > $O/cases_${ST}_n$n.log 2>&1 || V "vector gen n$n FAILED"; done
ebuild(){ # tag mut cases...
  local t=$1 m=$2; shift 2; local d=$O/obj_$t; rm -rf $d
  verilator --binary --timing --hierarchical -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
    --top-module tb_hnx_hc_eng4 +define+MUT=$m +define+OT_FP_DATA_NORST +define+HC_DRLY=2 +define+HC_XRLY=1 +define+HC_QDRLY=2 \
    -Mdir $d -o V$t rtl/hbm_next/hc/tb/tb_hnx_hc_eng4_hier.vlt "${ESRC[@]}" > $O/build_$t.log 2>&1
  V "build $t rc=$? bin=$( [ -x $d/V$t ] && echo ok || echo MISSING)"
  for c in "$@"; do
    local od=$O/run_${t}_$c; rm -rf $od; cp -r $O/cases_$ST/$c $od
    ( cd $od && $d/V$t $(cat plus.txt) > run.log 2>&1; echo RUN_RC=$? >> run.log
      V "$t $c: $(grep -h 'HC_ENG_DONE\|HC_ENG PASS\|HC_ENG FAIL\|FAULT\|MISMATCH\|watchdog\|RUN_RC' run.log | head -4 | tr '\n' ' ')" ) &
  done
  wait; rm -rf $d
  local np=0 nc=$#
  for c in "$@"; do grep -q '^HC_ENG PASS' $O/run_${t}_$c/run.log && np=$((np+1)); done
  [ $np = $nc ] && V "HNX_HC_RING MUT=$m PASS $np/$nc" || V "HNX_HC_RING MUT=$m FAIL $np/$nc (HC_ENG FAIL)"
  if [ $t = e0 ]; then
    V "HNX_HC_ROW_II $(python3 - $O <<'PY'
import re, sys, glob
pts = []
for f in glob.glob(sys.argv[1] + '/run_e0_n*/run.log'):
    m = re.search(r'npos=(\d+).*HC_MIX_CYCLES=(\d+)', open(f).read())
    if m: pts.append((int(m.group(1)), int(m.group(2))))
pts.sort(); n = len(pts)
if n < 2: print('n/a'); sys.exit()
mx = sum(p for p, _ in pts) / n; my = sum(c for _, c in pts) / n
ii = sum((p - mx) * (c - my) for p, c in pts) / sum((p - mx) ** 2 for p, _ in pts)
print('%.1f cycles/row; points %s' % (ii, ' '.join('N%d=%d' % pc for pc in pts)))
PY
)"
  fi
}
case $ST in e0) ebuild e0 0 n1 n2 n3 n4 n6 n8;; e4) ebuild e4 4 n4;; e1) ebuild e1 1 n4;; esac
V "done"
