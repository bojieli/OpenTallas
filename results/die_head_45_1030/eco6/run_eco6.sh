#!/bin/bash
# DIE-HEAD-45: LEP ECO6 GRT-stage ECO on the ECO5 f GRT DB (+ ECO5 f routed SPEF for the base report)
set -u
D=/srv/opentallas-scratch2/claude/die-head-45/eco6
K=/srv/opentallas-scratch2/claude/die-head-42/lep_eco4_kit
F=/srv/opentallas-scratch2/claude/die-head-44/lep_eco5_f_kit/run/results/asap7/hbc_ot_s81hd_lep_pair/base
G=/srv/opentallas-scratch2/claude/die-head-44/lep_eco5/f/eco5
mkdir -p $D/eco6
docker run --rm --name dh45-eco6-$$ --cpus=8 --memory=56g --memory-swap=56g -v "$K":/work:ro -v "$G":/base:ro -v "$F":/rbase:ro -v "$D":/out -v "$D/sdcdir":/sdc:ro -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc "set +e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -no_init -exit /out/eco6.tcl > /out/eco6/run.log 2>&1; rc=\$?
if test \$rc = 0; then python3 -I /work/clk_geom_diff.py /out/eco6/clock_lock/clk_freeze_pre.tsv /out/eco6/clock_lock/clk_after_grt.tsv --pre-unrouted --json /out/eco6/clock_diff.json > /out/eco6/clock_diff.log 2>&1; rc=\$?; fi
echo \$rc > /out/eco6/rc
chown -R \$HUID:\$HGID /out
exit \$rc"
