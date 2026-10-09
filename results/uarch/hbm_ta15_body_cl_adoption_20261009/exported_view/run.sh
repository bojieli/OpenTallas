#!/bin/bash
set -u
D=/srv/opentallas-scratch/codex/ta15-body-export-206798f3f
# same-final-objects6_report measured738888KB (~0.705GiB), round1GiB; exportactual peak pending.
/srv/opentallas-scratch/admit.sh 1 -- /usr/bin/time -v python3 "$D/source/tools/w18/export_view.py" --orfs-dir "$D/orfs" --name ot_hbm_production_clock_digital_body --post-sdc physical/hbm_accel_die_views/clock_boundary/production_body_cl.sdc --corners ss,tt,ff --out "$D/view" > "$D/export.log" 2>&1
echo $? > "$D/exit.rc"
