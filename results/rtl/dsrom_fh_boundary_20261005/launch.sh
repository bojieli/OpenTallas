#!/bin/bash
set -u
R=/srv/opentallas-scratch/codex/dsrom-fh-boundary-20261005
cd "$R/wt"
python3 -c 'import pathlib; assert float(pathlib.Path("/proc/loadavg").read_text().split()[0]) < 128, "EPYC2 load >=128"'
rc=$?
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
uptime
free -g
df -h /srv/opentallas-scratch
exec python3 tools/dsrom_fh_boundary_sta.py --route-base /srv/opentallas-scratch/claude/dsrom-fh-close/runs/C9u35/work/orfs/results/asap7/opentallas_ot_hdc_v41_fh_ctx_asap7_C9u35/base --context-sdc /srv/opentallas-scratch/claude/dsrom-fh-close/runs/C9u35/work/orfs/constraint.sdc --out "$R/measurement-r5"
