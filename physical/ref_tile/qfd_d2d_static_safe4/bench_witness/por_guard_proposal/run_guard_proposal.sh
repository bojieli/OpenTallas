#!/bin/bash
set -eu
iverilog -g2012 -DMUT_EARLY=0 -s tb -o guard_ok.vvp qw_por_root_guard_proposal.sv tb_qw_por_root_guard.sv
vvp guard_ok.vvp > guard_proposal_pass.log
iverilog -g2012 -DMUT_EARLY=1 -s tb -o guard_mut.vvp qw_por_root_guard_proposal.sv tb_qw_por_root_guard.sv
if vvp guard_mut.vvp > guard_proposal_mutant.log;then echo 'MUTANT_UNEXPECTED_PASS';exit 1;fi
docker run --rm -v /srv/opentallas-scratch/claude/codex-qw-d2d-clockdiag:/data openroad/orfs:asap7lock sh -c 'python3 /data/prepare_guard_lib.py && yosys -Q -T /data/map_guard.ys' > guard_map31.log 2>&1
