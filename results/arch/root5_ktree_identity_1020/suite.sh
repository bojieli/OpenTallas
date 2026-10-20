#!/bin/bash
set -eu
R=$PWD
mkdir -p base cand pylib
# Reuse the original complete source/resource archive and add exact current tools.
tar xf /srv/opentallas-scratch/claude/root5-tools-1020/base.tar -C base
tar xf /srv/opentallas-scratch/claude/root5-tools-1020/base.tar -C cand
tar xf current.tar -C base
tar xf current.tar -C cand
tar xzf /srv/opentallas-scratch/claude/root5-tools-1020/pylib.tar.gz --strip-components=1 -C pylib
for side in base cand; do
 (cd "$side" && git init -q && git unpack-objects < /srv/opentallas-scratch/claude/root5-tools-1020/objects.pack >/dev/null)
done
(cd cand && git apply ../candidate.patch)
cp test_ktree_buffer_identity.py cand/tools/ref_tile/tests/
export PYTHONPATH="$R/pylib"
set +e
(cd cand/tools/ref_tile && python3 -m pytest -p no:cacheprovider -q -o addopts="" tests/test_native_census.py tests/test_ktree_native_scope.py tests/test_ktree_buffer_identity.py > "$R/focused.log" 2>&1); echo $? > focused.rc
for side in base cand; do
 (cd "$side/tools/ref_tile" && python3 -m pytest -p no:cacheprovider -q -rfE -o addopts="" --continue-on-collection-errors . > "$R/${side}_ref_tile.log" 2>&1; echo $? > "$R/${side}_ref_tile.rc") &
done
wait
