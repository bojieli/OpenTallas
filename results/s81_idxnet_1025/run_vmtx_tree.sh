#!/usr/bin/env bash
# S81/IDXNET (2026-10-25): dsdv_bk_sel_vmtx DST / LOOP / tpn_i gate on the compiler's rank-tree compose bench
# (tools/s81_dv/layer_prog/bk/run_idx_tree.sh, DIEM=1 TXS=1, k3 fixture of results/rtl/codex_idxtx_local_1021: die 0
# root, die 1 -> ca, die 2 -> cb).  Cases (golden = lower_bk tree-rd-check, unchanged expectation):
#   regr      TP=0 (original bench mode)                       TX_MUT 0 PASS, TX_MUT 3 FAIL
#   tp0       TP=1, no TPD                                     PASS (DST 0 = H4 tree path, same edges)
#   tpd2      TP=1 +TPD=2 (die 1 via tpn_o -> root tpn_i)       PASS
#   tpd6      TP=1 +TPD=6 (dies 1 + 2 via tpn)                  PASS
#   loop1     TP=1 +LPD=1 (die 1 LOOP, DST 3)                   LOOP_OK > 0, LOOP_BAD 0, TP_STRAY 0 (tree verdict n/a)
#   mutants   IDX_MUT=1 (DST ignored) tpd2 FAIL; VM_MUT=1 (i_n copies from i_a) tpd2 FAIL; IDX_MUT=2 (lane not 3) loop1 LOOP_BAD > 0
# usage (cwd = repo root): run_vmtx_tree.sh OUT
set -u
O=${1:?out}; mkdir -p "$O"
R=tools/s81_dv/layer_prog/bk/run_idx_tree.sh
F=results/s81_idxnet_1025/fixture
mk() { mkdir -p "$O/$1"; cp $F/args.txt $F/exp.json "$O/$1/"; gzip -dc $F/stim.txt.gz > "$O/$1/stim.txt"; }
bad=0
want() { n=$1; exp=$2; f=$3
  v=$(grep -m1 -oE "TREE_RD (PASS|FAIL)" "$f" 2>/dev/null); echo "$n: $v (want $exp)"; [ "$v" = "TREE_RD $exp" ] || bad=1; }
export DIEM=1 TXS=1 J=${J:-16}
mk regr; TP=0 bash $R "$O/b" 0 "$O/regr" > "$O/regr_m0.out" 2>&1; want regr_m0 PASS "$O/regr_m0.out"
mk regr3; TP=0 bash $R "$O/b" 3 "$O/regr3" > "$O/regr_m3.out" 2>&1; want regr_m3 FAIL "$O/regr_m3.out"
for c in tp0: tpd2:+TPD=2 tpd6:+TPD=6; do n=${c%%:*}; x=${c#*:}; mk $n
  TP=1 EXTRA="$x" TAG=_$n bash $R "$O/b" 0 "$O/$n" > "$O/$n.out" 2>&1; want $n PASS "$O/$n.out"
  grep -h "TB_TREE_TP" "$O/$n"/run_*_$n.log; grep -q "tp_stray 0 " "$O/$n"/run_*_$n.log || { echo "  $n: TP stray"; bad=1; }
done
loopchk() { n=$1; mode=$2; l=$(grep -h "TB_TREE_TP" "$O/$n"/run_*_$n.log); echo "$n: $l"
  ok=$(echo "$l" | sed -E 's/.*loop_ok ([0-9]+).*/\1/'); lb=$(echo "$l" | sed -E 's/.*loop_bad ([0-9]+).*/\1/')
  if [ "$mode" = good ]; then [ "${ok:-0}" -gt 0 ] && [ "$lb" = 0 ] && echo "$l" | grep -q "tp_stray 0 " || bad=1
  else [ "${lb:-0}" -gt 0 ] || { echo "  $n: loop mutant not caught"; bad=1; }; fi; }
mk loop1; TP=1 EXTRA="+LPD=1" TAG=_loop1 bash $R "$O/b" 0 "$O/loop1" > "$O/loop1.out" 2>&1; loopchk loop1 good
mk mi1; TP=1 MUTDEF="-DIDX_MUT=1" EXTRA="+TPD=2" TAG=_mi1 bash $R "$O/b" 0 "$O/mi1" > "$O/mi1.out" 2>&1; want mut_idx1 FAIL "$O/mi1.out"
mk mv1; TP=1 MUTDEF="-DVM_MUT=1" EXTRA="+TPD=2" TAG=_mv1 bash $R "$O/b" 0 "$O/mv1" > "$O/mv1.out" 2>&1; want mut_vm1 FAIL "$O/mv1.out"
mk mi2; TP=1 MUTDEF="-DIDX_MUT=2" EXTRA="+LPD=1" TAG=_mi2 bash $R "$O/b" 0 "$O/mi2" > "$O/mi2.out" 2>&1; loopchk mi2 mut
[ $bad = 0 ] && echo "VMTX_TREE_GATE PASS" || echo "VMTX_TREE_GATE FAIL"; exit $bad
