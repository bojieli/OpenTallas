#!/bin/bash
# Placement-only physical trial from byte-identical, previously proved RTL.
# Copied synthesis outputs are cache seeds: ORFS may rebuild dependencies.
# A prior LEC receipt never qualifies a newly mapped output netlist.
# This never routes or claims sign-off; later promotion needs ordinary LEC.
set -euo pipefail
k=$1
mem=${2:-32}
cpu=${3:-8}
docker run --rm --name "codex-hbm-place-$$" --cpus="$cpu" --memory="${mem}g" --memory-swap="${mem}g" -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/sdc_lint.py /work --liberty $(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* | grep -v FAKE)
net=$(ls /work/run/results/asap7/*/base/1_2_yosys.v)
python3 -I /work/face_guard_core.py "$net" /work
python3 -I /work/port_bind_core.py "$net" /work
# Aggregate do-* targets only copy already-completed children in this ORFS.
# Exact copied synthesis outputs are newer than their byte-identical sources;
# ordinary targets therefore build the missing floorplan/placement children.
touch /work/run/results/asap7/*/base/1_*
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES='"$cpu"' place
odb=$(ls /work/run/results/asap7/*/base/3_place.odb)
ODB="$odb" OUT=/work/placed.csv openroad -python -exit /work/dump_placed.py
echo CODEX_PLACEMENT_ONLY_PASS
'
