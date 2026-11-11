#!/bin/bash
# FTLOCK-S81 STA probe on the routed late-ECO i1 DB (read-only mounts): preamble = signoff session.tcl lines 1-117
# (exact libs, odb, spef, golden sdc, uncertainty policy, propagated clocks) + probe commands.  usage: T CORNER(ff|tt) TAIL_TCL
set -u
T=$1; C=$2; TAIL=$3
F=/srv/opentallas-scratch2/claude/die-s81-85/ftlock; E=/srv/opentallas-scratch2/claude/die-s81-85/stt${T}_eco/i1
O=$F/sta/t${T}_$C; mkdir -p $O
head -n 117 $E/signoff/$C/session.tcl > $O/probe.tcl
cat $TAIL >> $O/probe.tcl
[ -f $F/sta/pairs_t${T}.txt ] && cp $F/sta/pairs_t${T}.txt $O/pairs.txt
docker run --rm --name ftlk_sta_${T}_${C}_$$ --cpus=4 --memory=48g --memory-swap=48g \
  -v $E/run/results/asap7/dp_slice_station__t${T}/base:/base:ro -v $E/signoff/$C/sdcdir:/sdc:ro -v $O:/out \
  -v $E:/work:ro -v $E/config.mk:/work/config.mk:ro openroad/orfs:asap7lock \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/probe.tcl > $O/probe.log 2>&1
echo "rc=$?" > $O/rc
docker run --rm -v $O:/out openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /out >/dev/null 2>&1
