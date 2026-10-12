#!/usr/bin/env bash
# Install one adopted tile view for the all-tile dsfd_engram_c composition (el1011-ds-misc/engram).  Run on the host that ran the job:
#   bash physical/s81_engc_tiles/compose/install_views.sh <job-name> <view-name> [<sram-macro-view-dir>]
# copies <run>/record/views/<view-name> (LEF + SS/FF from the job's collect stage) to physical/s81_engc_tiles/views/ and
# adds the TT liberty from the SAME route (tools/tt_views/view_export.py --corners tt), as engram_c_h's leaves.
set -euo pipefail
job=$1; name=$2; mv=${3:-}
RUN=${OT_CL_ROOT:-/srv/opentallas-scratch/claude/closure-loop}/$job
orfs=$(ls -d $RUN/routes/*/work/orfs | head -1)
out=physical/s81_engc_tiles/views/$name
mkdir -p "$out"
cp -a $RUN/record/views/$name/. "$out/"
python3 tools/tt_views/view_export.py --orfs-dir "$orfs" --name "$name" --out "$out" --corners tt \
  ${mv:+--macro-view $mv} --image openroad/orfs:asap7lock
ls "$out"
