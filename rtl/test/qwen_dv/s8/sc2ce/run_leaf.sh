#!/usr/bin/env bash
# QC-P5-TIE sc2 chain-end leaf lockstep.  Usage: bench.sh VAR MUTNET  (run in sc2src/); MUTNET 0 eq (+mut1 run), 1 CE_MUT=1 netlist, 2 CE_MUT=2 netlist
set -u; VAR=$1; MN=$2; O=bench/out_v${VAR}n${MN}; mkdir -p $O
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
F=$([[ $VAR == 0 ]] && echo dn0 || echo up0)
NET="out/$F/qfd_dv_s5_sc2_k79_$F.sv"; DEF=""
[[ $MN == 1 ]] && { NET="out/${F}m/qfd_dv_s5_sc2_k79_${F}_mut.sv"; DEF="+define+OT_S5_SC2CE_MUT_NETLIST"; }
[[ $MN == 2 ]] && { NET="out/${F}m2/qfd_dv_s5_sc2_k79_${F}_mut.sv"; DEF="+define+OT_S5_SC2CE_MUT_NETLIST"; }  # CE_MUT 2: valid RB word
$V --version > $O/verilator_version.txt
$V --binary -O1 -j 24 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 $DEF -GVAR=$VAR -GMUT_NET=$(( MN > 0 )) \
  --top-module tb_sc2_ce bench/tb_sc2_ce.sv bench/qfd_dv_s5_sc2_leaf.sv bench/qfd_dv_s5_sc2_ce_leaf.sv \
  out/repro/qfd_dv_s5_sc2_k79.sv out/repro/qfd_dv_s5_sc2_k79_helpers.sv $NET -Mdir $O/obj > $O/build.log 2>&1 || { echo BUILD_FAIL; grep -m10 %Error $O/build.log; exit 1; }
$O/obj/Vtb_sc2_ce > $O/run.log 2>&1; grep -m6 "SC2CE_MISMATCH\|SC2_CE_LOCKSTEP" $O/run.log
if [[ $MN == 0 ]]; then $O/obj/Vtb_sc2_ce +mut1 > $O/run_mut1.log 2>&1; grep -m3 "SC2CE_MISMATCH\|SC2_CE_LOCKSTEP" $O/run_mut1.log; fi
