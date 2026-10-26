#!/bin/bash
# stage_reuse.sh <archive_job_dir> <type> : copy a closed-archive routed run into a signoff.py-shaped kit on intel1
set -e
A=$1; T=$2; H=intel1; R=/srv/opentallas-scratch2/claude/kv-cores-1025r/reuse/$T
pa=$(ls -d $A/run/routes/*/physical_artifacts); route=$(dirname $pa)
nick=$(sed -n 's/^export DESIGN_NICKNAME = //p' $pa/config.mk)
ssh $H "mkdir -p $R/kit/run/results/asap7/$nick/base $R/kit/run/logs/asap7/$nick/base $R/kit/run/reports/asap7/$nick/base $R/archive_meta"
B=$R/kit/run/results/asap7/$nick/base
rsync -a $pa/config.mk $pa/constraint.sdc $H:$R/kit/
rsync -aL $A/final/6_final.odb.zst $A/final/6_final.spef.zst $pa/1_2_yosys.v.zst $H:$B/
[ -e $A/final/6_final.v.zst ] && rsync -aLL $A/final/6_final.v.zst $H:$B/
rsync -a $(ls $route/work/orfs/logs/asap7/*/base/5_2_route.json) $H:$R/kit/run/logs/asap7/$nick/base/
rsync -a $pa/5_route_drc.rpt $H:$R/kit/run/reports/asap7/$nick/base/
rsync -a $A/job.json $A/spec.json $A/manifest.json $A/commit.txt $route/corner_sta.json $route/signoff.sdc $H:$R/archive_meta/
ssh $H "cd $B && for f in *.zst; do zstd -qd --rm \$f; done; echo $A > $R/archive_meta/SOURCE; ls -la $B"
