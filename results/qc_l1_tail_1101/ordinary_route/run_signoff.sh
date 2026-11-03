#!/bin/bash
set -euo pipefail
K="$PWD"
B="$K/run/results/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base"
test -s "$B/6_final.odb"
test -s "$B/6_final.spef"
test -s "$B/6_final.sdc"
exec python3 -I "$K/released_signoff_bundle/signoff.py" run --run-dir "$K/run" --kit "$K" --sdc "$B/6_final.sdc" --out "$K/signoff_p_qc" --image openroad/orfs:asap7lock --docker "$K/sta_docker.sh" --corners tt,ff --margin-policy nominal > signoff_p_qc.log 2>&1
