#!/bin/bash
set -e
R=/srv/opentallas-scratch2/claude/codex-head-collect-1030
K=$R/hb4_dpl2_kit
O=$R/lep_data_eco2
mkdir -p "$O/sdcdir" "$O/clock_lock"
cp "$K/constraint.sdc" "$O/sdcdir/golden.sdc"
DK=docker
$DK ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name head-lep-data-eco2-$$ --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work:ro -v "$K/run/results/asap7/hbc_ot_s81hd_lep_pair/base":/base:ro -v "$O":/out -v "$O/sdcdir":/sdc:ro -v "$R/clock_recipe.py":/clock_recipe.py:ro -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc 'set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -no_init -exit /out/eco.tcl > /out/run.log 2>&1
python3 -I /work/clk_geom_diff.py /out/clock_lock/clk_freeze_pre.tsv /out/clock_lock/clk_after_grt.tsv --pre-unrouted --json /out/clock_diff.json > /out/clock_diff.log 2>&1
ACTION=verify INPUT_ODB=/out/5_1_grt.odb RECIPE=/work/clock_infra_recipe.json REPORT=/out/verify_clock_recipe.json openroad -python -exit /clock_recipe.py > /out/verify_clock_recipe.log 2>&1
chown -R $HUID:$HGID /out'
echo $? > "$O/rc"
