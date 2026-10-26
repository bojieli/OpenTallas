#!/bin/bash
set -u
R=$(pwd)
mkdir -p pylib base cand
tar xzf pylib.tar.gz --strip-components=1 -C pylib
tar xf base.tar -C base
tar xf base.tar -C cand
(cd cand && git apply --binary ../cand.patch) || exit 3
export PYTHONPATH="$R/pylib"
for side in base cand; do
 (cd "$side" && python3 -m pytest -p no:cacheprovider -q -rfE -o addopts="" tools/die_safety > "$R/${side}.log" 2>&1; echo $? > "$R/${side}.rc") &
done
wait
cat base.log cand.log
echo BASE_RC=$(cat base.rc) CAND_RC=$(cat cand.rc)
tar czf result_logs.tar.gz base.log cand.log base.rc cand.rc
echo RESULT_BEGIN
base64 -w0 result_logs.tar.gz
echo
echo RESULT_END
