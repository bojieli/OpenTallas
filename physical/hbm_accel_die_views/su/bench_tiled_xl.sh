#!/bin/bash
# [su] hbm-phys-1010: tiled R25GPHT4 su quarter (192 hfd_su_tile_xl, 456-bit acc, per-tile ot_cg_tile, 2 face wake
# stages) transaction bench: qid 0-3 exact vs the generator model, inject-gate mutant, lane-connectivity negative and
# never-wake / 20-edge-late wake mutants must FAIL (late: settle != 46).  Regenerates the RTL from the committed generator and checks it matches the committed set.
#   bench_tiled_xl.sh <outdir>   (run in the source root)
set -u; O=$1; mkdir -p $O; R=physical/hbm_accel_die_views/su/rtl_tiled_xl_r25
python3 tools/hbm_hub_quarter_gen.py --quarter su --ports physical/hbm_accel_die_views/su/r25gpht4_wake_contract/ports.json \
  --out $O/gen --tiled --cg --cg-input-stages 2 --xroot lockup --lane-size 85.32 162.0 > $O/plan.log 2>&1
for f in hfd_su.sv hfd_su_neg.sv hfd_su_tile_xl.sv tb_hfd_su.sv macro_place.tcl; do cmp -s $O/gen/$f $R/$f || echo "REPRO_MISMATCH $f"; done > $O/result.txt
C="$(pwd)/rtl/hbm_accel/cg/ot_cg_tile.sv $(pwd)/rtl/hdc/ot_hdc_cg.sv"
cd $O/gen
run() { n=$1; shift; iverilog -g2012 -o $n.vvp "$@" $C > $n.clog 2>&1 && timeout 7200 vvp -n $n.vvp > $n.log 2>&1; echo "$n rc=$? $(grep OT_RESULT $n.log)" >> ../result.txt; rm -f $n.vvp; }
for q in 0 1 2 3; do run pos$q -Ptb.QID=$q tb_hfd_su.sv hfd_su.sv hfd_su_tile_xl.sv ot_su12_light_simstub.sv & done; wait
run gmut -Ptb.QID=1 -DOT_HFD_SU_MUT_NOGATE tb_hfd_su.sv hfd_su.sv hfd_su_tile_xl.sv ot_su12_light_simstub.sv &
run neg tb_hfd_su.sv hfd_su_neg.sv hfd_su_tile_xl.sv ot_su12_light_simstub.sv &
# gating is in the data path: never waking must FAIL; a wake 20 edges after the input must change the settle
# (the RTL MUT_LATE=4 mutant is absorbed by the quarter's face-chain lead, so the schedule is mutated at the source)
sed 's/#0.1 cg_en = 1; repeat (5)/#0.1 cg_en = 0; repeat (5)/' tb_hfd_su.sv > tb_nowake.sv
sed 's/#0.1 cg_en = 1; repeat (5) @(posedge clk); #0.1;/repeat (5) @(posedge clk); #0.1; fork begin repeat (20) @(posedge clk); cg_en = 1; end join_none/' tb_hfd_su.sv > tb_late.sv
cmp -s tb_nowake.sv tb_hfd_su.sv && echo "MUTANT_NOT_APPLIED nowake" >> ../result.txt
cmp -s tb_late.sv tb_hfd_su.sv && echo "MUTANT_NOT_APPLIED late" >> ../result.txt
run nowake tb_nowake.sv hfd_su.sv hfd_su_tile_xl.sv ot_su12_light_simstub.sv &
run late tb_late.sv hfd_su.sv hfd_su_tile_xl.sv ot_su12_light_simstub.sv &
wait
cd ..
P=$(grep -c '^pos[0-3] rc=0 .*mismatches=0 settle_cycles=46$' result.txt)
M=$(grep -cE '^(gmut|neg|nowake) .*mismatches=[1-9]' result.txt)
LS=$(grep '^late ' result.txt | sed -n 's/.*settle_cycles=\([0-9]*\).*/\1/p'); { grep -qE '^late .*mismatches=[1-9]' result.txt || { [ -n "$LS" ] && [ "$LS" != 46 ]; }; } && M=$((M+1))
grep -qE 'REPRO_MISMATCH|MUTANT_NOT_APPLIED' result.txt && R1=FAIL || R1=OK
echo "TILED_XL_BENCH repro=$R1 positives_pass=$P/4 (settle 46 = ungated) mutants_fail=$M/4" | tee -a result.txt
[ $R1 = OK ] && [ $P = 4 ] && [ $M = 4 ] && echo TILED_XL_BENCH_PASS
