#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
D=$(cd -- "$(dirname -- "$0")" && pwd)
sudo docker run --rm --memory 2g --memory-swap 2g -v "$D:$D" -w "$D" openroad/orfs:latest yosys -Q -p "read_slang --top top $D/pad.sv; prep -top top -flatten; sat -prove mismatch 0 -verify" > "$D/slang.log" 2>&1
if sudo docker run --rm --memory 2g --memory-swap 2g -v "$D:$D" -w "$D" openroad/orfs:latest yosys -Q -p "read_slang -D MUT --top top $D/pad.sv; prep -top top -flatten; sat -prove mismatch 0 -verify" > "$D/mutant.log" 2>&1; then echo MUTANT_ESCAPED; exit 1; fi
echo PASS_DEFAULT_AND_CONNECTED_MUTANT_CAUGHT
