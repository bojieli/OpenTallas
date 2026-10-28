#!/bin/bash
set -eu
B=$(cd "$(dirname "$0")" && pwd)
for c in base5 base6 base7 lock6 lock_mut6 lock_short5 decode7 decode8 decode_wrong8; do
 docker run --rm --user "$(id -u):$(id -g)" -v "$B:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -s "/work/$c.ys" >"$B/$c.log" 2>&1
done
