#!/usr/bin/env bash
set -uo pipefail
source /home/ubuntu/.opentallas-env
cd /srv/opentallas/repos/goodall-collective-fanout-12f63a664
ulimit -t unlimited
ulimit -f unlimited
ulimit -v unlimited
free -b > /srv/opentallas-scratch/jobs/boole-collective-txmask-die-u12-12f63a664-r1/headroom.txt
df -B1 /srv/opentallas-scratch >> /srv/opentallas-scratch/jobs/boole-collective-txmask-die-u12-12f63a664-r1/headroom.txt
uptime >> /srv/opentallas-scratch/jobs/boole-collective-txmask-die-u12-12f63a664-r1/headroom.txt
bash tools/hbm_collective_txmask_fanout_route.sh die-u12 /srv/opentallas-scratch/jobs/boole-collective-txmask-die-u12-12f63a664-r1/route boole_coll_txmask_die_u12_r1
rc=$?
echo rc=$rc > /srv/opentallas-scratch/jobs/boole-collective-txmask-die-u12-12f63a664-r1/exit
exit $rc
