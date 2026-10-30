#!/bin/bash
set -e
R=/srv/opentallas-scratch2/claude/codex-head-collect-1030/serdes_reshape
E=$R/eco1b
K=$R/eco1
mkdir -p "$E/sdcdir"
cp "$K/constraint.sdc" "$E/sdcdir/golden.sdc"
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name head-serdes-data-eco1b-$$ --cpus=4 --memory=24g --memory-swap=24g -v "$K":/work:ro -v "$K/run/results/asap7/hbc_ot_s81_kp4_dchn/base":/base:ro -v "$E":/out -v "$E/sdcdir":/sdc:ro -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1;openroad -no_init -exit /out/eco1b.tcl > /out/run.log 2>&1;rc=$?;echo $rc > /out/rc;chown -R $HUID:$HGID /out;exit $rc'
python3 "$K/clk_geom_diff.py" "$E/clock_lock/clk_freeze_pre.tsv" "$E/clock_lock/clk_after_grt.tsv" --pre-unrouted --json "$E/clock_diff.json" > "$E/clock_diff.log"
