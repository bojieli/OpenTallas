#!/bin/bash
set -euo pipefail
R="$PWD"
D=$(find "$R/native_synth_out/landw116v2" -name 1_2_yosys.raw.v -printf '%h\n')
cp results/arch/qw_landw_fan32_1020/synth/{flatten.py,audit.py,constant_roles.py} "$D/"
docker run --rm --network none -v "$D:/out" openroad/orfs:asap7lock python3 /out/constant_roles.py > "$D/constant_roles.log" 2>&1
docker run --rm --network none -v "$D:/out" openroad/orfs:asap7lock python3 /out/flatten.py > "$D/flatten.log" 2>&1
(cd "$D"; python3 audit.py)
