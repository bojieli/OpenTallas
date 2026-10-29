#!/bin/bash
# HBM-CORES-KITS-1 diagnostic probe (copy of kit): rtl_lint.py + generic yosys synth cell estimate. probe.sh KIT
set -u
K=$1; N=$(basename $K); P=/srv/opentallas-scratch2/claude/hbm-cores-kits-1/probe/$N
rm -rf $P; mkdir -p $P; cp -a $K/. $P/
TOP=$(python3 -c "import json;print(json.load(open('$P/freeze.json')).get('design') or '')" 2>/dev/null); [ -z "$TOP" ] && TOP=$(echo $N | sed 's/_[0-9a-f]\{12\}-.*//')
docker run --rm --name hck1probe-$(echo $N | cut -c1-40 | tr -c 'A-Za-z0-9_.-' _)-$$ --cpus=4 --memory=48g --memory-swap=48g -v $P:/work -w /work openroad/orfs:asap7lock bash -lc "
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1; echo LINT_RC=\$? > /work/probe_lint.rc
 grep -v -E '^(check|hierarchy|stat|tee)' /work/rtl_lint.ys | grep -E '^(read|verilog_defines)' > /work/est.ys
 printf 'hierarchy -check -top $TOP\nsynth -flatten -top $TOP\ntee -o /work/est_stat.txt stat\n' >> /work/est.ys
 timeout 5400 yosys -q -s /work/est.ys > /work/est.log 2>&1; echo EST_RC=\$? >> /work/probe_lint.rc
 chown -R $(id -u):$(id -g) /work"
cat $P/probe_lint.rc; grep -m1 -E "Number of cells" $P/est_stat.txt
