#!/bin/bash
cd /srv/opentallas-scratch/codex/hbm-service-striped-20261008/controller-allocated-r1
export PINNED_SOURCE_COMMIT=e100721e7
/srv/opentallas-scratch/admit.sh 1 -- python3 tools/hbm_native_index_control_bench.py --work minimum-gate >minimum-admission.log 2>&1
printf "%s\n" "$?" > minimum-terminal.exit
/srv/opentallas-scratch/admit.sh 8 -- python3 tools/hbm_svc_iks_prefetch_bench.py --portal 1 --control 1 --compact --work join-gate --out join-record.json >join-admission.log 2>&1
printf "%s\n" "$?" > join-terminal.exit
