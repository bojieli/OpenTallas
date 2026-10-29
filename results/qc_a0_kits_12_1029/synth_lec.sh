#!/bin/bash
# QC-A0-KITS-12: NK both-reset candidate SYNTH + lint + face_guard + native LEC (profile = rstwave proved native profile, every relation re-proved)
set -euo pipefail
R=/srv/opentallas-scratch2/claude/qc-a0-kits-12-1029
k=$R/kits/qfd_tile_nk_a0c_a0nk12rstboth
sudo docker run --rm --name qca0k12-nkboth-synth --cpus=8 --memory=32g --memory-swap=32g -v "$k":/work -v "$R/nk_rstwave_native_profile.json":/profile.json:ro -v "$R/lec_profile_run.py":/lec_profile_run.py:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1
python3 -I /work/sdc_lint.py /work --liberty $(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* | grep -v FAKE) > /work/sdc_lint.log 2>&1
python3 -I /work/selrange_gate.py /work > /work/selrange.log 2>&1 & lint_pid=$!
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 synth
wait "$lint_pid"
top=$(sed -n "s/^export DESIGN_NAME = //p" /work/config.mk)
netlist=$(ls /work/run/results/asap7/*/base/1_synth.v)
python3 -I /work/face_guard_core.py "$netlist" "$top" "$(cat /work/face_guard_skip.txt)" /work/pins.json /work/face_guard.json
python3 /lec_profile_run.py /work /profile.json /work/lec_profile
' > "$k/synth_lec.log" 2>&1
