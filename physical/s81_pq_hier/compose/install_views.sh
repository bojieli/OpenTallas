#!/usr/bin/env bash
# Install one adopted tile view for the PQ screen composition (el1011-ds-misc/pqc).  Run on the host that ran the job:
#   bash physical/s81_pq_hier/compose/install_views.sh <job-name> <view-name> [<sram-macro-view-dir>]
# copies <run>/record/views/<view-name> (LEF + SS/FF from the job's collect stage) to physical/s81_pq_hier/views/ and
# adds the TT liberty from the SAME route (tools/tt_views/view_export.py --corners tt), as engram_c_h's leaves.
set -euo pipefail
job=$1; name=$2; mv=${3:-}
RUN=/srv/opentallas-scratch/claude/closure-loop/$job
orfs=$(ls -d $RUN/routes/*/work/orfs | head -1)
out=physical/s81_pq_hier/views/$name
mkdir -p "$out"
cp -a $RUN/record/views/$name/. "$out/"
python3 tools/tt_views/view_export.py --orfs-dir "$orfs" --name "$name" --out "$out" --corners tt \
  ${mv:+--macro-view $mv} --image openroad/orfs:asap7lock
ls "$out"
