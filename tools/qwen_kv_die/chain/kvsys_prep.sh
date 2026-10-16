#!/bin/bash
# qwen-split/kvsys v1.1 (2026-10-14): local prep of one KV/system die chain run, from a CLEAN committed tree.
#   case (kv_die.py case --kv-wq-mirror --split) -> die_top_lint stubs -> ASSUMED element libs (frames, relays) -> closed
#   real views bound (bind_views.py) -> phi - R compensated die clocks (kvsys_clocks.py) -> NO-STUBS port bind
#   (die_port_bind_kv.py) -> per-bit 2-D window check (kvsys_window.py).  Then rsync OUT to the host and run
#   die_chain.sh kv with OT_STA_CLOCKS=<run>/libs/clocks_{corner}.tcl OT_CORNERS="tt ff ss" (SS = sensitivity only).
# usage: kvsys_prep.sh OUT
set -eu
O=$(readlink -f $1); S=$(cd $(dirname $0)/../../.. && pwd); cd $S
[ -z "$(git status --porcelain -- tools rtl physical)" ] || { echo "dirty tree: commit first"; exit 2; }
mkdir -p $O/libs
# v1.4 (OT_KV_HOST_V14=1): real HOST root core + 128 die-placed PC slices + PLL model (kv_die.py --host-v14)
H14=; V14=
if [ "${OT_KV_HOST_V14:-0}" = 1 ]; then H14=--host-v14; V14=,host_v14; fi
# v1.4.1 (OT_KV_HOST_NORTH=1): the HOST root core directly below the static D2D end (kv_die.py --host-north)
if [ "${OT_KV_HOST_NORTH:-0}" = 1 ]; then H14="--host-v14 --host-north"; V14=,host_v14,host_north; fi
# v1.4.2 (OT_KV_TREES=1, needs OT_KV_HOST_NORTH=1): HOST reset / boot fan-outs as registered relay trees (kv_die.py --host-trees)
if [ "${OT_KV_TREES:-0}" = 1 ]; then H14="$H14 --host-trees"; V14=$V14,host_trees; fi
# v1.4.3 (OT_KV_V143=1, needs OT_KV_TREES=1): G3S2 staged head ingress on the closed gather / sstage views, near-head
# feed-through frames, grown groups, regional reset roots (kv_die.py --v143)
BV=
if [ "${OT_KV_V143:-0}" = 1 ]; then H14="$H14 --v143"; V14=$V14,v143
  BV="--view qkd_hgs=physical/ref_tile/qkh_head_gather_stage/views/qkh_head_gather_stage --view qkd_hss=physical/ref_tile/qkh_head_sstage/views/qkh_head_sstage"; fi
python3 tools/qwen_kv_die/kv_die.py case --kv-wq-mirror --split $H14 --out $O/case_kv > $O/case.log
git rev-parse --short=9 HEAD > $O/case_kv/SOURCE_COMMIT
python3 tools/die_top_lint.py lint --die qwen_kv --variant kv_wq_mirror,split$V14 --out $O/lint > $O/lint.log 2>&1
# v1.2: the relays are REAL RTL generated from the die direction model (one flop a bit, per-bit direction) + its bench
python3 tools/qwen_kv_die/kv_relays.py --stubs $O/lint/qwen_kv_lint_top_stubs.sv --out $O/case_kv/qkd_kv_relays.sv \
  --json $O/relays.json --bench $O/tb_qkd_kv_relays.sv > $O/relays.log
for mu in 0 2; do
  python3 tools/qwen_kv_die/kv_relays.py --stubs $O/lint/qwen_kv_lint_top_stubs.sv --out $O/rly_mut$mu.sv --mut $mu > /dev/null
  iverilog -g2012 -o $O/rly_mut$mu.vvp $O/rly_mut$mu.sv $O/tb_qkd_kv_relays.sv && vvp -n $O/rly_mut$mu.vvp | tail -1 > $O/relays_bench_mut$mu.txt
done
grep -q 'RELAY_BENCH PASS' $O/relays_bench_mut0.txt && grep -q 'RELAY_BENCH FAIL' $O/relays_bench_mut2.txt || { echo "relay bench gate FAILED"; exit 3; }
rm -f $O/rly_mut*.vvp $O/rly_mut*.sv
python3 tools/qwen_die_element_lib.py --stubs $O/lint/qwen_kv_lint_top_stubs.sv --lef $O/case_kv/elements.lef --out $O/libs > $O/libs.log
for c in tt ff ss; do cp physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy/ot_hbm3e_phy_$c.lib $O/libs/ 2>/dev/null || true; done
python3 tools/qwen_kv_die/bind_views.py --split --case $O/case_kv --libs $O/libs \
  --view qkd_cdc_wleaf=physical/ref_tile/qkd_cdc_wleaf_ref/views/qkd_cdc_wleaf \
  --view qkd_kvwq_leaf_s_w129_m=physical/ref_tile/qkd_kvwq_leaf_s_w129_m/views/qkd_kvwq_leaf_s_w129_m \
  --view qkd_kvwq_ctl_bin=physical/ref_tile/qkd_kvwq_ctl_bin/views/qkd_kvwq_ctl_bin $BV \
  --out $O/libs/views.json > $O/bind.log
# v1.3: DIE-PLACED LEAVES: wires-only parent frames -> their CLOSED leaves at the planned sub-slots, each on its own view
# (OT_KV_EXPAND = comma list of frame masters, default all that kv_expand.py knows; 'none' keeps the frames)
EXP=
if [ "${OT_KV_EXPAND:-all}" != none ]; then
  python3 tools/qwen_kv_die/kv_expand.py --run $O $( [ "${OT_KV_EXPAND:-all}" = all ] || echo --only ${OT_KV_EXPAND} ) > $O/expand.log
  EXP="--expanded $O/expand.json"
fi
# v1.4: the host SerDes and the UCIe PHY bind their native ports (tx_up / tx_v / tx_flit / rx_v / rx_flit): SerDes <-> root core phy_*, UCIe <-> qkd_d2d_static fdi_* (583 b)
[ -n "$H14" ] && python3 tools/qwen_kv_die/kv_native_phy.py --case $O/case_kv > $O/native_phy.log \
  && python3 tools/qwen_kv_die/kv_native_phy.py --case $O/case_kv --libs $O/libs >> $O/native_phy.log
python3 tools/qwen_kv_die/kvsys_clocks.py --case $O/case_kv --views $O/libs/views.json --out $O/libs > $O/clocks.log
python3 tools/qwen_kv_die/die_port_bind_kv.py $O/case_kv/die.v --split --relay-rtl $O/case_kv/qkd_kv_relays.sv $EXP --out $O/port_bind.json > $O/port_bind.log
python3 tools/qwen_kv_die/kvsys_window.py --split $H14 --out $O/window.json > $O/window.log
echo "prep done: $(cat $O/case_kv/SOURCE_COMMIT) $(tail -1 $O/bind.log | head -c 300)"
