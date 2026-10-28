#!/bin/bash
set -eu
B=/srv/opentallas-scratch2/claude/codex-s81-ve-lec-0359/zero_ring_miter
for c in pass7 short6 mut7;do
 docker run --rm --user "$(id -u):$(id -g)" -v "$B:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -Q -s "/work/$c.ys" >"$B/$c.log" 2>&1
done
