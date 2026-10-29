#!/bin/bash
set -euo pipefail
while ssh epyc2 docker inspect -f '{{.State.Running}}' codex-qcore-symmetric-place 2>/dev/null | grep -q true; do sleep 15; done
ssh epyc2 test -f /srv/opentallas-scratch2/claude/codex-qcore-1028/kit/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base/3_place.odb
ot-run --hosts epyc2 --mem 8 --threads 2 --dir /srv/opentallas-scratch2/claude/codex-qcore-1028 -- bash /srv/opentallas-scratch2/claude/hbm-cores-kits-5/aptools/geom_check.sh /srv/opentallas-scratch2/claude/codex-qcore-1028/geom_place
