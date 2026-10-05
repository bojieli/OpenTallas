#!/bin/bash
set -u
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
/srv/opentallas-scratch/admit.sh 2 -- bash /srv/opentallas-scratch/jobs/euclid-svc-aq-block-directed-r1/body.sh > /srv/opentallas-scratch/jobs/euclid-svc-aq-block-directed-r1/supervisor-body.log 2>&1
echo $? > /srv/opentallas-scratch/jobs/euclid-svc-aq-block-directed-r1/exit
