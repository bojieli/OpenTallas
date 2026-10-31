#!/bin/bash
R=/srv/opentallas-scratch2/claude/die-kv-47-hr/tx
docker run --rm --name kv47hr-tx-rtl --cpus 6 --memory 96g --memory-swap 96g -v "$R":/work openroad/orfs:asap7lock bash /work/inner.sh
