#!/usr/bin/env bash
# DIE-HBM-96 DRT-0073 candidate view for one signed master. Args: MASTER VIEWDIR ODB X Y DIEW DIEH
set -u
M=$1; V=$2; O=$3; X=$4; Y=$5; W=$6; H=$7
P=/srv/opentallas-scratch2/claude/die-hbm-96/pa3/$M; IMG=openroad/orfs:asap7lock; OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
mkdir -p $P/src; cd $P; cp -f ../abstract_detail.py ../make_tracks.tcl .
test -s $O || { echo NO_ODB $O; exit 3; }
ls -la $O | cut -c25-
ln -f $O src/6_final.odb 2>/dev/null || cp $O src/6_final.odb
cp -f $V/$M.lef base.lef; sha256sum base.lef | cut -c1-16
CTRL=$(python3 -I -c "
import re
t=open('base.lef').read()
for m in re.finditer(r'PIN (\w+)\n\s+DIRECTION INPUT',t):
    if m[1] not in ('clk',): print(m[1]); break")
echo control pin: ${CTRL:-none}
for p in clk $CTRL; do printf 'module t(input %s);\n %s u(.%s(%s));\nendmodule\n' $p $M $p $p > top_$p.v; done
run() { # lef tag
  L=$1; T=$2
  cat > pa_$T.tcl <<TCL
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef \$P/asap7_tech_1x_201209.lef
read_lef \$P/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /p/$L
read_verilog /p/top_\$::env(PIN).v
link_design t
initialize_floorplan -die_area "0 0 $W $H" -core_area "1.08 1.08 [expr $W-2] [expr $H-2]" -site asap7sc7p5t
source /p/make_tracks.tcl
place_macro -macro_name u -location {$X $Y} -orientation R0
place_pins -hor_layers M4 -ver_layers M5
set_routing_layers -signal M2-M7
pin_access -verbose 1
puts "PA_OK \$::env(PIN)"
exit
TCL
  for p in clk $CTRL; do timeout 200 docker run --rm --name h96_${T}_$p --memory=16g --cpus=4 -e PIN=$p -v $P:/p $IMG bash -c "$OR -no_init -threads 4 -exit /p/pa_$T.tcl" > lp_${T}_$p.txt 2>&1; echo "== $T $p rc $?"; grep -E 'DRT-0073|PA_OK|^\[ERROR' lp_${T}_$p.txt | cut -c1-160; done
}
run base.lef base
for BF in 1 0; do
  python3 -I abstract_detail.py tcl --odb /p/src/6_final.odb --out /p/detail$BF.lef --bloat-factor $BF > detail$BF.tcl
  timeout 300 docker run --rm --name h96_d$BF --memory=16g --cpus=4 -v $P:/p $IMG bash -c "$OR -no_init -threads 4 -exit /p/detail$BF.tcl" > log_d$BF.txt 2>&1; echo detail $BF rc $?
  python3 -I abstract_detail.py splice --base base.lef --detail detail$BF.lef --out new$BF.lef --layers M5,M6 --pin-clear-um 0.048 --pin-clear-layers M5 > splice$BF.json 2>splice$BF.err; rc=$?; echo splice $BF rc $rc
  [ $rc = 0 ] || { head -c 900 splice$BF.json; tail -2 splice$BF.err | cut -c1-200; continue; }
  python3 -I -c "
import json;d=json.load(open('splice$BF.json'));print({k:d.get(k) for k in ('rects','pin_clear','detail_pins_equal_base','check_ok','problems','out_sha256')})"
  python3 -I abstract_detail.py check --base base.lef --new new$BF.lef > check$BF.json; echo check $BF rc $?; cut -c1-200 check$BF.json
  mkdir -p n$BF; cp -f new$BF.lef n$BF/$M.lef
  run n$BF/$M.lef n$BF
  grep -q PA_OK lp_n${BF}_clk.txt && { echo SELECT bf$BF; break; }
done
echo DONE
