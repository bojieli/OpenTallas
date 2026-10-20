#!/bin/bash
set -u
R=$PWD
mkdir -p pylib base cand
tar xzf pylib.tar.gz --strip-components=1 -C pylib
tar xf base.tar -C base
tar xf base.tar -C cand
(cd cand && git apply --binary ../cand.patch) || exit 3
for side in base cand; do
 (cd "$side" && git init -q && git unpack-objects < ../objects.pack >/dev/null)
done
export PYTHONPATH="$R/pylib"
for side in base cand; do
 for cohort in closure_loop ref_tile fleet landed_parent; do
  (cd "$side/tools/$cohort" && python3 -m pytest -p no:cacheprovider -q -rfE -o addopts="" --continue-on-collection-errors --deselect test_ot_run_load_hold.py::Rebalance::test_single_host_waits_unbounded_and_max_wait_is_kept . > "$R/${side}_${cohort}.log" 2>&1; echo $? > "$R/${side}_${cohort}.rc") &
 done
done
wait
python3 compare.py
(cd cand/tools/ref_tile && python3 -m pytest -q -o addopts="" tests/test_gate_only_binding.py tests/test_raw_macro_clocks.py tests/test_pg_standard_bind.py tests/test_hybrid_clock_entries.py > "$R/focused.log" 2>&1); echo $? > focused.rc
python3 pg_batch.py > pg_batch.log 2>&1; echo $? > pg_batch.rc
