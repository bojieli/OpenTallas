#!/bin/bash
set -e
K=/srv/opentallas-scratch2/claude/codex-head-collect-1030/serdes_reshape/eco1b_kit
B=$K/run/results/asap7/hbc_ot_s81_kp4_dchn/base
test -s "$B/6_final.v"
DK=docker
$DK ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name head-serdes-eco1b-routedlec-$$ --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc 'set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set +e
python3 -I /work/lec.py /work --netlist /work/run/results/asap7/hbc_ot_s81_kp4_dchn/base/6_final.v --out /work/lec_routed > /work/firstdrt/lec_routed.log 2>&1
rc=$?;echo $rc > /work/firstdrt/lec_routed.rc
chown -R $HUID:$HGID /work/lec_routed /work/firstdrt
exit $rc'
