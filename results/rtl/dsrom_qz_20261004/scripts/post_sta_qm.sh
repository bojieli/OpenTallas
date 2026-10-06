#!/bin/bash
# Z23 (margin-first) post-route STA: the run is routed at PER (0.770 ns); sign-off at 0.833 ns re-times the routed design with
# its own SDC, period 833 and the max input delays + (833 - PER) (the same internal pin -> flop budget).  Writes post-CTS SS
# (at PER), final SS / FF at 833 (setup ends listed up to +80 ps: the +60 ps target), and the classify / io dumps.
# usage: post_sta_qm.sh RUN WT JROOT
R=$1; WT=$2; T=$3
J=$T/jobs/$R; S=$T/sta/$R; mkdir -p $S
SD=$WT/results/rtl/dsrom_qz_20261004/scripts
sed 's/-slack_max 0 > \$::env(OUT).ends/-slack_max 80 > $::env(OUT).ends/' $SD/sta_corner.tcl > $S/sta_m80.tcl
sta() { # name corner odb sdc spef tcl
  docker run --rm -v $T:$T -v $WT:/src -e NPATH=300 -e CORNER=$2 -e ODB=$3 -e SDC=$4 -e SPEF=$5 -e OUT=$S/$1 openroad/orfs:latest \
   bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit $6" > $S/$1.log 2>&1; echo $? > $S/$1.rc; }
B() { ls -d $J/work/orfs/results/asap7/*/base 2>/dev/null | head -1; }
until [ -n "$(B)" ] && [ -f "$(B)/4_1_cts.odb" ] || [ -f $J/launch.done ]; do sleep 60; done
[ -f "$(B)/4_1_cts.odb" ] && sta cts_SS SS $(B)/4_1_cts.odb $(B)/4_cts.sdc "" $S/sta_m80.tcl
until [ -f $J/launch.done ]; do sleep 120; done
if [ -f "$(B)/6_final.odb" ]; then
  P=$(awk '/create_clock/{for(i=1;i<=NF;i++) if($i=="-period") print $(i+1)}' $(B)/6_final.sdc | head -1)
  python3 - "$(B)/6_final.sdc" "$S/signoff_833.sdc" "$P" <<'PY'
import re, sys
src, dst, per = sys.argv[1], sys.argv[2], float(sys.argv[3])
d = 833.0 - per
out = []
for l in open(src):
    l = re.sub(r"-period [0-9.]+", "-period 833.0000", l)
    m = re.match(r"(set_input_delay )([0-9.]+)( .*-max .*)", l)
    if m: l = f"{m[1]}{float(m[2]) + d:.4f}{m[3]}\n"
    out.append(l)
open(dst, "w").write("".join(out))
PY
  sta final_SS SS $(B)/6_final.odb $S/signoff_833.sdc $(B)/6_final.spef $S/sta_m80.tcl &
  sta final_FF FF $(B)/6_final.odb $S/signoff_833.sdc $(B)/6_final.spef $SD/sta_corner.tcl &
  sta per_SS SS $(B)/6_final.odb $(B)/6_final.sdc $(B)/6_final.spef $SD/sta_corner.tcl &
  sta cls_SS SS $(B)/6_final.odb $S/signoff_833.sdc $(B)/6_final.spef $SD/classify.tcl &
  sta io_SS SS $(B)/6_final.odb $S/signoff_833.sdc $(B)/6_final.spef $SD/io.tcl &
  sta io_FF FF $(B)/6_final.odb $S/signoff_833.sdc $(B)/6_final.spef $SD/io.tcl &
  wait
fi
echo done > $S/post.done
