#!/usr/bin/env bash
# S81/IDXNET (2026-10-25): iqf benches, Verilator 5.050 (daemon version).  usage (cwd = repo root): run_idx_qfs.sh OUT
#   qf    tb_dsdv_idx_qf  MUT 0 PASS; MUT 1 / 2 FAIL                                  (qf IDX_S rewrite, qc0 never valid from ql)
#   qfs   tb_dsdv_idx_qfs MUT 0 PASS; MUT 1, SMUT 1, +DSDV_IDX_QF_MUT_FWDALL FAIL     (root frame -> exact 2-beat qc)
set -u
O=${1:?out}; mkdir -p "$O"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
I=rtl/dsrom_sys/s81_dv/idx
( sha256sum $I/dsdv_idx_tree.sv $I/dsdv_idx_qfs.sv $I/test/tb_dsdv_idx_qf.sv $I/test/tb_dsdv_idx_qfs.sv; $VL --version ) > "$O/sources.sha256"
bad=0
one() { n=$1; top=$2; want=$3; shift 3
  $VL --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN "$@" --top-module $top $I/dsdv_idx_tree.sv $I/dsdv_idx_qfs.sv \
      $I/dsdv_idx_bsplit.sv $I/test/$top.sv --Mdir "$O/obj_$n" > "$O/build_$n.log" 2>&1 || { echo "BUILD FAIL $n"; grep -m5 %Error "$O/build_$n.log"; bad=1; return; }
  "$O/obj_$n/V$top" > "$O/run_$n.log" 2>&1
  tag=$([ $top = tb_dsdv_idx_qf ] && echo TB_QF || echo TB_QFS)
  v=$(grep -E "^$tag (PASS|FAIL)$" "$O/run_$n.log" | tail -1)
  [ "$v" = "$tag $want" ] && echo "CASE OK $n: $v" || { echo "CASE BAD $n: got '$v' want $want"; bad=1; }
}
one qf_m0 tb_dsdv_idx_qf PASS -GMUT=0
one qf_m1 tb_dsdv_idx_qf FAIL -GMUT=1
one qf_m2 tb_dsdv_idx_qf FAIL -GMUT=2
one qfs_m0 tb_dsdv_idx_qfs PASS -GMUT=0
one qfs_m1 tb_dsdv_idx_qfs FAIL -GMUT=1
one qfs_s1 tb_dsdv_idx_qfs FAIL -GSMUT=1
one qfs_fwd tb_dsdv_idx_qfs FAIL +define+DSDV_IDX_QF_MUT_FWDALL
[ $bad = 0 ] && echo "IQF_GATE PASS" || echo "IQF_GATE FAIL"; exit $bad
