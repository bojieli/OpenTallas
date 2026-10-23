#!/bin/bash
set -uo pipefail
BASE=$(pwd)
COMMIT=d3b64cd692856a35f8b5292c046874699a23d454
mkdir -p logs
ln -s ../codex-kv-reset-pair-2205/frozen.tar.gz frozen.tar.gz
echo "$COMMIT" > BASE_COMMIT
sha256sum frozen.tar.gz candidate_parser.py candidate_test.py > SOURCE_SHA256
mkdir -p baseline candidate
tar -xzf frozen.tar.gz -C baseline || exit 5
tar -xzf frozen.tar.gz -C candidate || exit 5
cp candidate_parser.py candidate/tools/textbook_lint.py
cp candidate_test.py candidate/tools/ref_tile/test_async_reset_landing_shape.py
for variant in baseline candidate; do
 for suite in closure_loop ref_tile hier_contract tt_views; do
  echo "$(date -Is) START $variant $suite" | tee -a STATUS.log
  (cd "$BASE/$variant" && python3 -m unittest discover -s "tools/$suite") > "logs/${variant}_${suite}.log" 2>&1
  rc=$?
  echo "$rc" > "logs/${variant}_${suite}.rc"
  echo "$(date -Is) END $variant $suite rc=$rc" | tee -a STATUS.log
 done
done
echo "$(date -Is) PAIR_COMPLETE" | tee -a STATUS.log
