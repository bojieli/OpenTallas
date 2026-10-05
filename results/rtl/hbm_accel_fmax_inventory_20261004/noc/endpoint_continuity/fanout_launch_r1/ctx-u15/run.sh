#!/usr/bin/env bash
set -uo pipefail
source /home/ubuntu/.opentallas-env
cd /srv/opentallas/repos/goodall-collective-fanout-12f63a664
ulimit -t unlimited
ulimit -f unlimited
ulimit -v unlimited
free -b > /srv/opentallas-scratch/jobs/goodall-collective-txmask-ctx-u15-12f63a664-r1/headroom.txt
df -B1 /srv/opentallas-scratch >> /srv/opentallas-scratch/jobs/goodall-collective-txmask-ctx-u15-12f63a664-r1/headroom.txt
uptime >> /srv/opentallas-scratch/jobs/goodall-collective-txmask-ctx-u15-12f63a664-r1/headroom.txt
# Runner requires exclusive freshoutput, separate from immutable supervisor log.
bash tools/hbm_collective_txmask_fanout_route.sh ctx-u15 /srv/opentallas-scratch/jobs/goodall-collective-txmask-ctx-u15-12f63a664-r1/route goodall_coll_txmask_ctx_u15_r1
rc=$?
printf 'rc=%s\n' \"$rc\" > /srv/opentallas-scratch/jobs/goodall-collective-txmask-ctx-u15-12f63a664-r1/exit
exit $rc
