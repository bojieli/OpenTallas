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
python3 tools/qwen_kv_die/kv_die.py case --kv-wq-mirror --split --out $O/case_kv > $O/case.log
git rev-parse --short=9 HEAD > $O/case_kv/SOURCE_COMMIT
python3 tools/die_top_lint.py lint --die qwen_kv --variant kv_wq_mirror,split --out $O/lint > $O/lint.log 2>&1
python3 tools/qwen_die_element_lib.py --stubs $O/lint/qwen_kv_lint_top_stubs.sv --lef $O/case_kv/elements.lef --out $O/libs > $O/libs.log
for c in tt ff ss; do cp physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy/ot_hbm3e_phy_$c.lib $O/libs/ 2>/dev/null || true; done
python3 tools/qwen_kv_die/bind_views.py --split --case $O/case_kv --libs $O/libs \
  --view qkd_cdc_wleaf=physical/ref_tile/qkd_cdc_wleaf_ref/views/qkd_cdc_wleaf \
  --view qkd_kvwq_leaf_s_w129_m=physical/ref_tile/qkd_kvwq_leaf_s_w129_m/views/qkd_kvwq_leaf_s_w129_m \
  --view qkd_kvwq_ctl_bin=physical/ref_tile/qkd_kvwq_ctl_bin/views/qkd_kvwq_ctl_bin \
  --out $O/libs/views.json > $O/bind.log
python3 tools/qwen_kv_die/kvsys_clocks.py --case $O/case_kv --views $O/libs/views.json --out $O/libs > $O/clocks.log
python3 tools/qwen_kv_die/die_port_bind_kv.py $O/case_kv/die.v --split --out $O/port_bind.json > $O/port_bind.log
python3 tools/qwen_kv_die/kvsys_window.py --split --out $O/window.json > $O/window.log
echo "prep done: $(cat $O/case_kv/SOURCE_COMMIT) $(tail -1 $O/bind.log | head -c 300)"
