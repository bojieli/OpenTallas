#!/bin/bash
# S81-DIE5 dsfd_dvland_pvrd bench (iverilog): base at dL 300 / 700 / 1100 ps (K 2 / 2 / 3), slip, MUT1
cd "$(dirname "$0")"; set -u
iverilog -g2012 -o b_base tb_dsfd_dvland_pvrd.sv dsfd_dvland_pvrd.sv ot_s81_land.sv || exit 2
iverilog -g2012 -DMUT1 -o b_mut1 tb_dsfd_dvland_pvrd.sv dsfd_dvland_pvrd.sv ot_s81_land.sv || exit 2
for a in "DL=300 K=2" "DL=700 K=2" "DL=1100 K=3" "DL=300 K=2 NW=160" ; do echo "base $a"; vvp -n b_base $(for x in $a; do echo +$x; done) | grep -E "OT_PVRD|PVRD_RESULT"; done
echo "slip"; vvp -n b_base +DL=300 +K=2 +SLIP=1 | grep -E "OT_PVRD|PVRD_RESULT"
echo "mut1 (expect FAIL)"; vvp -n b_mut1 +DL=300 +K=2 | grep -E "OT_PVRD|PVRD_RESULT"
