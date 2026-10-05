#!/bin/bash
set -u
source ~/.opentallas-env
job=/srv/opentallas-scratch/codex/boole-item8-bira-20261005/route_v1
src=/srv/opentallas/repos/boole-item8-bira-route-v1
cd "$src" || exit 1
export OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
git rev-parse HEAD > "$job/source_sha"
date -u > "$job/started"
/srv/opentallas-scratch/admit.sh 16 -- python3 -u tools/run_abi3_physical.py --view asap7 \
 --top ot_v41_mbist_shell_bira_pipe --param POP_PIPE=1 \
 --source rtl/dft/v41/ot_v41_mbist_shell_bira_pipe.sv --source rtl/dft/ot_mbist_ctrl_bira_pipe.sv \
 --source rtl/dft/ot_mbist_bira_pipe.sv --source rtl/dft/ot_mbist_rom_collar_par.sv --source rtl/dft/ot_mbist_sram_collar.sv \
 --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --false-path-io --stages synth,pnr \
 --core-utilization 30 --place-density 0.55 --hold-margin-ns 0.01 \
 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 20 --nickname-tag mbist_bira_pipe_v1 \
 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --keep-workdir "$job/work" --force --output "$job/physical.json" > "$job/run.log" 2>&1
rc=$?; echo "$rc" > "$job/physical.exit"
# Routed data, including a routed miss, must get the required actual SS/FF analysis.
if [ -f "$job/physical.json" ]; then
 python3 -u tools/w18/corner_sta.py --orfs-dir "$job/work/orfs" --output "$job/corner_sta.json" > "$job/corner.log" 2>&1
 echo "$?" > "$job/corner.exit"
fi
echo "$rc" > "$job/route.exit"
date -u > "$job/finished"
exit "$rc"
