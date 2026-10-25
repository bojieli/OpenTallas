#!/bin/bash
# TOK-QK/C 10-24: build + run the closed-loop hub_Wi host-link sub-bench (gen_chw.py) on a C-applied staged tree.
#   run_chw.sh STAGED_C_TREE REC FRAMES OUT [J]
#   STAGED_C_TREE = staged vehicle after kv43/apply_C.sh; REC = whole-die hub_Wi input record (partrec, BO1 hub_Wi);
#   FRAMES = boot bundle frames.hex.  Builds OUT/obj (C) and OUT/obj_mut (mutant ii: fdicdc/mut_direct.sv instead of
#   ot_fdi_phy_cdc.sv), runs phase x skew sweep + mutants, writes OUT/summary.txt.  Flat build ~30 s / ~2 GB; runs 1 thread.
set -u
H=$(cd "$(dirname "$0")" && pwd); KD=$(cd $H/.. && pwd); V=$(readlink -f $1); REC=$(readlink -f $2); FR=$(readlink -f $3)
O=$(mkdir -p $4 && readlink -f $4); J=${5:-24}
BO1=${BO1_HUBWI:-/srv/opentallas-scratch2/claude/codex-qwen/boot_bo1_bound_candidate/kv3_hub_Wi_part.sv}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P0=$(head -1 $V/files.f | sed 's#/src/.*##')
for f in files.f incdirs.f hostside.f; do sed "s#$P0#$V#g" $V/$f > $O/$f; done
grep -v -e '/qkd_pll_analog_model.sv$' -e '/qwen_kvsys_bound_top.sv$' $O/files.f > $O/f.tmp && mv $O/f.tmp $O/files.f
grep -v '/c1c2__rtl/ot_fdi_phy_cdc.sv$' $O/files.f > $O/files_mut.f; echo "$KD/fdicdc/mut_direct.sv" >> $O/files_mut.f
python3 $H/gen_chw.py $V/src/bind__rtl/kv3_hub_Wi_part.sv $BO1 $O || exit 2
F="--binary --timing -O1 --x-assign fast --x-initial fast -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD -Wno-PINMISSING -Wno-MODDUP -Wno-MULTITOP --timescale 1ns/1ps -j 16 --top-module tb_chw +define+KVS_FAR=tb_chw +incdir+$H $KD/kvs_link_phy_models.sv $O/tb_chw.sv -CFLAGS -O1"
( cd $O && /usr/bin/time -v $VL $F -f hostside.f -f files.f -f incdirs.f -Mdir obj > build.log 2>&1 ) || { echo BUILD FAIL; grep -m5 %Error $O/build.log; exit 2; }
( cd $O && /usr/bin/time -v $VL $F -f hostside.f -f files_mut.f -f incdirs.f -Mdir obj_mut > build_mut.log 2>&1 ) || { echo BUILD MUT FAIL; grep -m5 %Error $O/build_mut.log; exit 2; }
echo "built $(grep -E 'Elapsed|Maximum res' $O/build.log | tr -s ' ' | tr '\n' ' ')"
: > $O/jobs.txt
for ph in 0 131 263 397 521 677 811 977; do for sk in 0 1; do
  echo "nom_ph${ph}_sk$sk obj +PHASE_PS=$ph +PHY_SKEW_RAND=$((ph + sk * 7 + 1))" >> $O/jobs.txt; done; done
echo "nom_tp1000 obj +TP_PS=1000 +PHASE_PS=200 +PHY_SKEW_W=3 +PHY_SKEW_E=0" >> $O/jobs.txt
echo "nom_tp1050 obj +TP_PS=1050 +PHASE_PS=500 +PHY_SKEW_W=0 +PHY_SKEW_E=5" >> $O/jobs.txt
for ph in 0 397 811; do
  echo "mutC1_ph$ph obj +PHASE_PS=$ph +MUT_C1" >> $O/jobs.txt
  echo "mutDIRECT_ph$ph obj_mut +PHASE_PS=$ph" >> $O/jobs.txt
done
run1() { n=$1; b=$2; shift 2; mkdir -p $O/runs/$n; ( cd $O/runs/$n && /usr/bin/time -f "%e s %M KB" -o time $O/$b/Vtb_chw +verilator+error+limit+1000000 +REP=$REC +FRAMES=$FR "$@" > sim.log 2>&1 ); }
export -f run1; export O REC FR
cat $O/jobs.txt | xargs -P $J -L 1 bash -c 'run1 "$@"' _
: > $O/summary.txt
while read n b rest; do
  echo "$n | $(grep -m1 -E '^CHW (PASS|FAIL)' $O/runs/$n/sim.log | cut -c1-330) | errors $(grep -c '%Error' $O/runs/$n/sim.log) | $(grep -m1 SERDES_PHY_MODEL $O/runs/$n/sim.log | cut -c18-) $(grep SERDES_PHY_MODEL $O/runs/$n/sim.log | sed -n 2p | cut -c18-) | $(cat $O/runs/$n/time)" >> $O/summary.txt
done < $O/jobs.txt
cat $O/summary.txt
