#!/bin/bash
set -eu
k=/srv/opentallas-scratch2/claude/codex-qca0/nk-icg0-v3
trap 'sudo chown -R "$(id -u):$(id -g)" "$k"' EXIT
sudo docker run --rm --cpus 8 --memory 24g --memory-swap 24g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -eu
python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1
python3 -I /work/sdc_lint.py /work --liberty $(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* | grep -v FAKE) > /work/sdc_lint.log 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/mm_patch.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 synth
python3 -I /work/selrange_gate.py /work > /work/selrange.log 2>&1
n=$(find /work/run/results/asap7 -name 1_synth.v | head -n 1)
python3 -I /work/face_guard_core.py "$n" qfd_tile_nk_a0c "$(cat /work/face_guard_skip.txt)" /work/pins.json /work/face_guard.json
ny=$(find /work/run/results/asap7 -name 1_2_yosys.v | head -n 1)
python3 -I /work/lec.py /work --netlist "$ny" --out /work/lec > /work/lec_run.log 2>&1 &
lec_pid=$!
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 cts
set +e
wait "$lec_pid"
lr=$?
set -e
if [ "$lr" = 1 ]; then echo "LEC NOT EQUIVALENT: prototype stopped"; exit 5; fi
if [ "$lr" != 0 ]; then echo "LEC WARNING exit $lr recorded; no SIGNED claim"; fi
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 SKIP_INCREMENTAL_REPAIR=1 do-5_1_grt
' > "$k/trial3.log" 2>&1
