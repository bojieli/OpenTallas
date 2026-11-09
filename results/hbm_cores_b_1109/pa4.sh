#!/usr/bin/env bash
# DIE-HBM-96: which splice forms reach pin access, without the pin-clear cut. Args: MASTER LAYERSETS(space-sep, comma layers)
set -u
M=$1; shift
P=/srv/opentallas-scratch2/claude/die-hbm-96/pa3/$M; IMG=openroad/orfs:asap7lock; OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
cd $P
python3 -I -c "
import importlib.util as u
s=u.spec_from_file_location('a','abstract_detail.py');a=u.module_from_spec(s);s.loader.exec_module(a)
print('default_layers',a.default_layers(open('base.lef').read().splitlines(keepends=True)))"
for BF in 1 0; do
 test -s detail$BF.lef || { python3 -I abstract_detail.py tcl --odb /p/src/6_final.odb --out /p/detail$BF.lef --bloat-factor $BF > detail$BF.tcl; timeout 300 docker run --rm --name h96_d$BF --memory=16g --cpus=4 -v $P:/p $IMG bash -c "$OR -no_init -threads 4 -exit /p/detail$BF.tcl" > log_d$BF.txt 2>&1; echo detail $BF rc $?; }
 for LS in "$@"; do
  T=b${BF}_${LS//,/_}; python3 -I abstract_detail.py splice --base base.lef --detail detail$BF.lef --out $T.lef --layers $LS > $T.json 2>$T.err; rc=$?
  python3 -I -c "
import json;d=json.load(open('$T.json'));print('$T splice rc $rc',{k:d.get(k) for k in ('rects','detail_pins_equal_base','check_ok','problems')})"
  mkdir -p d_$T; cp -f $T.lef d_$T/$M.lef; sed "s#/p/n1/$M.lef#/p/d_$T/$M.lef#" pa_n1.tcl > pa_$T.tcl
  timeout 200 docker run --rm --name h96_${T} --memory=16g --cpus=4 -e PIN=clk -v $P:/p $IMG bash -c "$OR -no_init -threads 4 -exit /p/pa_$T.tcl" > lp_$T.txt 2>&1; echo "== $T clk rc $?"; grep -E 'DRT-0073|PA_OK|^\[ERROR' lp_$T.txt | head -2 | cut -c1-140
 done
done
