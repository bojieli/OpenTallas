#!/usr/bin/env bash
# Use an existing compiled real composed executable; no new RTL or reset.
set -euo pipefail
cd "${COMPOSED_STAGE:?actual stage}"
sha256sum out/composed vectors/* vectors-layer1/* > out/transition_inputs.sha256
out/composed vectors transition vectors-layer1 > out/transition.log 2>&1
cat out/transition.log
