#!/bin/bash
set -uo pipefail
BASE=$(pwd)
COMMIT=d3b64cd692856a35f8b5292c046874699a23d454
mkdir -p logs
if [ ! -d repo/.git ]; then
 git clone --shared --no-checkout /srv/opentallas-scratch/claude/git-mirror/OpenTallas.git repo > logs/clone.log 2>&1 || exit 2
 git -C repo remote set-url origin https://github.com/bojieli/OpenTallas.git
fi
git -C repo fetch --no-tags origin "$COMMIT" > logs/fetch.log 2>&1 || exit 3
echo "$COMMIT" > BASE_COMMIT
# Both variants start from the same complete frozen git archive, including every fixture.
if [ ! -s frozen.tar.gz ]; then
 git -C repo archive --format=tar "$COMMIT" | gzip -1 > frozen.tar.gz.tmp || exit 4
 mv frozen.tar.gz.tmp frozen.tar.gz
fi
sha256sum frozen.tar.gz candidate_parser.py candidate_test.py > SOURCE_SHA256
mkdir -p baseline candidate
tar -xzf frozen.tar.gz -C baseline || exit 5
tar -xzf frozen.tar.gz -C candidate || exit 5
cp candidate_parser.py candidate/tools/textbook_lint.py
cp candidate_test.py candidate/tools/ref_tile/tests/test_async_reset_landing_shape.py
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
