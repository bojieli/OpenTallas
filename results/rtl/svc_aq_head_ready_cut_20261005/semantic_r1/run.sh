#!/bin/bash
set -u
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
cd /srv/opentallas/repos/euclid-svc-aq-head-ready-973696-20261005
/srv/opentallas-scratch/admit.sh 2 -- bash tools/svc_aq_head_ready_lockstep.sh /srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-semantic-r1/exact >/srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-semantic-r1/gate.log 2>&1
echo $? >/srv/opentallas-scratch/jobs/euclid-svc-aq-head-ready-semantic-r1/exit
