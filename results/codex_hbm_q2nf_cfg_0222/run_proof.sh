#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-q2nf-cfg-0222
DK=docker
$DK ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --memory=8g --memory-swap=8g --cpus=2 -v "$R":/work -w /work openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set +e
yosys -Q -T -p "read_verilog -sv actual_cfg_ref.sv ot_bodyctl_cfg_case.sv miter.sv; hierarchy -check -top q2nf_cfg_miter; proc; flatten; opt; sat -verify -prove ok 1 -show-inputs" > good.log 2>&1
good=$?
yosys -Q -T -p "read_verilog -sv actual_cfg_ref.sv mut_cfg_case.sv miter.sv; hierarchy -check -top q2nf_cfg_miter; proc; flatten; opt; sat -verify -prove ok 1 -show-inputs" > mutant.log 2>&1
mutant=$?
printf "good_rc %s\nmutant_rc %s\n" "$good" "$mutant" > proof.rc
chown -R 1000:1000 /work
[ "$good" = 0 ] && [ "$mutant" != 0 ] && grep -q "proof did fail" mutant.log
'
