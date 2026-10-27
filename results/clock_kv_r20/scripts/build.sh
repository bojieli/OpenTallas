#!/bin/bash
# CLOCK-KV-R20: R19 build command unchanged (R19 inputs), tool = R20 worktree (stub split annotation)
cd /srv/opentallas-scratch2/claude/clock-kv-r20-1027; export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r19-1027/in/pylib:/srv/opentallas-scratch2/claude/wt/clock-kv-r20/tools/die_plan; ulimit -v 64000000
python3 /srv/opentallas-scratch2/claude/wt/clock-kv-r20/tools/die_plan/die_clock_mesh.py build /srv/opentallas-scratch2/claude/clock-kv-r19-1027/in/hm_r12.json --out r20b --nx 32 --ny 71 --m 2 --rep-um 450 --ndr 4w --max-move 500 --hop-max 405 --reserve-cell-sites --lattice-spec /srv/opentallas-scratch2/claude/clock-kv-r19-1027/lat_r19.json --track-file /srv/opentallas-scratch2/claude/clock-kv-r19-1027/in/kit/grt/tracks.tcl --delta-id D-KV-CLK-R19 > r20b.log 2>&1
echo "rc=$? $(date -Is)" > r20b.run
