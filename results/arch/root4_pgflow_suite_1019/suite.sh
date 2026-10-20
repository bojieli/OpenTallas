#!/bin/bash
# ROOT4 10-19: base (merge 08b3d3a9e) vs cand (claude/root4-pgflow-1019) pytest cohort; v2 of ROOT3's suite
# + deselect the ot-run test that hung both sides (test_single_host_waits_unbounded) + per-side timeout.
set -u
R=$(pwd)
rm -rf pylib base cand; mkdir -p pylib base cand
tar xzf pylib.tar.gz --strip-components=1 -C pylib
tar xf base.tar -C base; tar xf base.tar -C cand; (cd cand && git apply --binary ../cand.patch) || { echo PATCH_FAIL; exit 3; }
export PYTHONPATH="$R/pylib"
T="tools/ref_tile tools/closure_loop tools/landed_parent tools/fleet tools/tt_views
   tools/qwen_kv_die/test_kv_param_native_audit.py tools/qwen_kv_die/test_kv_pc_rland.py tools/qwen_kv_die/test_kv_retirement.py
   tools/qwen_kv_die/test_kv_static.py tools/qwen_kv_die/test_kv_static_params.py tools/qwen_kv_die/test_kv_static_ectl_pair.py
   tools/qwen_split/test_d2d_txdp.py tools/qwen_split/test_collective_calendar.py"
DS="--deselect tools/fleet/test_ot_run_load_hold.py::Rebalance::test_single_host_waits_unbounded_and_max_wait_is_kept"
for v in base cand; do
  ( cd $v && timeout 4000 python3 -m pytest -p no:cacheprovider -rfE -v --continue-on-collection-errors $DS $T > "$R/$v.log" 2>&1; echo $? > "$R/$v.rc" ) &
done
wait
for v in base cand; do grep -E '^(FAILED|ERROR) ' $R/$v.log | sed 's/ - .*//' | sort -u > $R/$v.fail; echo "$v rc=$(cat $R/$v.rc) $(tail -1 $R/$v.log)"; done
echo "NEW in cand:"; comm -13 $R/base.fail $R/cand.fail
echo "FIXED in cand:"; comm -23 $R/base.fail $R/cand.fail
