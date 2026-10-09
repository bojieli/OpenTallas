#!/bin/bash
cd /srv/opentallas-scratch/codex/hbm-service-striped-20261008/controller-join-r1
export PINNED_SOURCE_COMMIT=9bcc33f84
/srv/opentallas-scratch/admit.sh 8 -- python3 tools/hbm_svc_iks_prefetch_bench.py --portal 1 --control 1 --work control-gate --out control-record.json >control-admission.log 2>&1
printf "%s\n" "$?" > control-terminal.exit
/srv/opentallas-scratch/admit.sh 8 -- python3 tools/hbm_svc_iks_prefetch_bench.py --portal 1 --early 1 --work early-gate --out early-record.json >early-admission.log 2>&1
printf "%s\n" "$?" > early-terminal.exit
