#!/bin/bash
set -eu
mkdir -p base cand
tar xf base.tar -C base
tar xf base.tar -C cand
(cd cand && git apply ../candidate.patch)
cp test_ktree_buffer_identity.py cand/tools/ref_tile/tests/
python3 actual_final.py > actual.log 2>&1
