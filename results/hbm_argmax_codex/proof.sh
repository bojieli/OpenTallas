#!/bin/bash
set -u
r=/srv/opentallas-scratch2/claude/wt/codex-hbm-argmax-1027/results/hbm_argmax_codex
for v in tree tree_mut; do
 sudo docker run --rm --memory 8g -v "$r:/work" -w /work openroad/orfs:asap7lock bash -c "yosys -p 'read_verilog -sv $v.sv; proc; opt; equiv_make tree_old tree_new m; hierarchy -top m; equiv_simple; equiv_induct; equiv_status -assert'" > "$r/$v.log" 2>&1
 echo "$v rc=$?"
done
