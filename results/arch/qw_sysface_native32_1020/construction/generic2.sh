#!/bin/bash
set -eu
D=/srv/opentallas-scratch2/claude/codex-qw-sysface-review-1020/top_intermediate
cd "$D"
docker run --rm -v "$D:/work" -w /work openroad/orfs:asap7lock yosys -Q -T -s generic2.ys > generic2.log 2>&1
