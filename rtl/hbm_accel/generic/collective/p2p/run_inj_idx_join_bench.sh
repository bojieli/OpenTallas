#!/usr/bin/env bash
# Bench + mutants for ot_hgi_coll_inj_idx_join (H-NETLIST/coll 0030). PASS = MUT0 PASS and MUT1..4 FAIL.
set -u
D=$(cd "$(dirname "$0")" && pwd)
O=${OUT:-$(mktemp -d)}
rc=0
for m in 0 1 2 3 4; do
  iverilog -g2012 -P tb_hgi_coll_inj_idx_join.MUT=$m -o "$O/tb$m" "$D/tb_hgi_coll_inj_idx_join.sv" "$D/ot_hgi_coll_inj_idx_join.sv" || exit 2
  r=$(vvp -n "$O/tb$m" | tail -2 | tr '\n' ' ')
  echo "MUT=$m $r"
  if [ $m -eq 0 ]; then case "$r" in *PASS*) ;; *) rc=1;; esac
  else case "$r" in *FAIL*) ;; *) rc=1;; esac; fi
done
[ $rc -eq 0 ] && echo "INJ_IDX_JOIN_BENCH PASS" || echo "INJ_IDX_JOIN_BENCH FAIL"
exit $rc
