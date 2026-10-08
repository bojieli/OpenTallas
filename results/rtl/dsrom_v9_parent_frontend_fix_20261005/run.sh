#!/bin/bash
set -eu
B=/srv/opentallas-scratch2/codex/fspine-v9-parent-context-20261005/pq0_fault_lowering_r3
bash "$B/pre_guard.sh"
for pq in 0 1; do
 docker run --rm --cpus=1 -v "$B":/out --entrypoint /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys openroad/orfs:latest -Q -T -p "read_slang --top ot_v41_pair_pq_ld_frontend -G PQ=$pq /out/fixed.sv; hierarchy -top ot_v41_pair_pq_ld_frontend; proc; opt; write_rtlil /out/pq${pq}_fixed.rtlil; write_verilog -noattr /out/pq${pq}_fixed.v" > "$B/pq${pq}_fixed.log" 2>&1
done
printf '0
' > "$B/terminal.exit"
