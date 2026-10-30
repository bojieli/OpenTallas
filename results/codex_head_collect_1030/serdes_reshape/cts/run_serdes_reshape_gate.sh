#!/bin/bash
set -e
R=/srv/opentallas-scratch2/claude/codex-head-collect-1030/serdes_reshape
K=$R/kit
mkdir -p "$R/postcts"
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
for c in TT FF;do
 $DK run --rm --name head-serdes-reshape-gate-$c-$$ --cpus=4 --memory=16g --memory-swap=16g -v "$K":/work -e ODB=/work/run/results/asap7/hbc_ot_s81_kp4_dchn/base/4_cts.odb -e OT_CORNER=$c -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1;openroad -exit /work/postcts_gate.tcl > /work/postcts_actual_${OT_CORNER}.log 2>&1;rc=$?;chown -R $HUID:$HGID /work;exit $rc'
done
