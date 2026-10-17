#!/usr/bin/env bash
# ot_hgi_coll_inj_idx_join_rg (HBM-TILES-B 10-17): (1) the original bench retargeted to the rg (MUT0 PASS, MUT1..4 FAIL),
# (2) random lockstep vs the original (PASS), skewed clk_r1 (FAIL), slot mutant (FAIL). PASS line: INJ_IDX_JOIN_RG_BENCH PASS.
# Usage: run_inj_idx_join_rg_bench.sh [bench:<m> | lockstep:<m>]  -> that one run only; exit 0 iff it prints PASS
#        (mutant job benches, expect=fail). No argument: the full bench.
set -u
D=$(cd "$(dirname "$0")" && pwd)
O=${OUT:-$(mktemp -d)}; mkdir -p "$O"
rc=0
SEL=${1:-}
BM="0 1 2 3 4"; LM="0 1 2"
case "$SEL" in bench:*) BM=${SEL#bench:}; LM="";; lockstep:*) BM=""; LM=${SEL#lockstep:};; "") ;; *) echo "bad selector $SEL"; exit 2;; esac
sed -e 's/ot_hgi_coll_inj_idx_join #(/ot_hgi_coll_inj_idx_join_rg_flat #(/' -e 's/dut(.clk(clk),.rst_n/dut(.clk_r0(clk),.clk_r1(clk),.rst_n/' \
    -e 's/module tb_hgi_coll_inj_idx_join;/module tb_hgi_coll_inj_idx_join_rgx;/' "$D/tb_hgi_coll_inj_idx_join.sv" > "$O/tb_rgx.sv"
for m in $BM; do
  iverilog -g2012 -P tb_hgi_coll_inj_idx_join_rgx.MUT=$m -o "$O/tb$m" "$O/tb_rgx.sv" "$D/ot_hgi_coll_inj_idx_join_rg.sv" || exit 2
  r=$(vvp -n "$O/tb$m" 2>&1 | grep -Ev '\$finish|^VCD' | tail -2 | tr '\n' ' ')
  echo "BENCH MUT=$m $r"
  if [ $m -eq 0 ]; then case "$r" in *PASS*) ;; *) rc=1;; esac; else case "$r" in *FAIL*) ;; *) rc=1;; esac; fi
done
for m in $LM; do
  iverilog -g2012 -P tb_hgi_coll_inj_idx_join_rg_lockstep.MUT=$m -o "$O/ls$m" "$D/tb_hgi_coll_inj_idx_join_rg_lockstep.sv" \
    "$D/ot_hgi_coll_inj_idx_join.sv" "$D/ot_hgi_coll_inj_idx_join_rg.sv" || exit 2
  r=$(vvp -n "$O/ls$m" | grep CIJ_RG_LOCKSTEP | tr '\n' ' ')
  echo "LOCKSTEP MUT=$m $r"
  if [ $m -eq 0 ]; then case "$r" in *PASS*) ;; *) rc=1;; esac; else case "$r" in *FAIL*) ;; *) rc=1;; esac; fi
done
if [ -n "$SEL" ]; then case "$r" in *PASS*) exit 0;; *) exit 1;; esac; fi
[ $rc -eq 0 ] && echo "INJ_IDX_JOIN_RG_BENCH PASS" || echo "INJ_IDX_JOIN_RG_BENCH FAIL"
exit $rc
