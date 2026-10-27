#!/bin/bash
# KV-PLAN-DELTA-3: CLOCK-KV mesh rebuild on the hm_r26q5 G12 PG grid (R22 recipe results/clock_kv_r22/upstream/scripts/run_build.sh, plan + kit swapped)
set -e; cd /srv/opentallas-scratch2/claude/kv-plan-q5-1027; ulimit -v 64000000; export PYTHONPATH=/srv/opentallas-scratch2/claude/kv-cores-pv3/pylib:/srv/opentallas-scratch2/claude/wt/kv-plan-q5-1027/tools/die_plan
python3 /srv/opentallas-scratch2/claude/wt/kv-plan-q5-1027/tools/die_plan/die_clock_mesh.py build pd/hm_r26q5.json --out mesh_q5 --nx 32 --ny 71 --m 2 --rep-um 450 --ndr 4w --max-move 500 --hop-max 405 --reserve-cell-sites --lattice-spec lat_r22.json --track-file kit_q5/grt/tracks.tcl --delta-id D-KV-PG-G12 > mesh_q5.log 2>&1
echo BUILD_DONE
