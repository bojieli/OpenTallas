#!/bin/bash
# fill-8 2026-10-10: transaction-exact bench of the TILED half-width SFU quarter (hfd_sfu = 16 hfd_sfu_tile macros,
# tools/hbm_hub_quarter_gen.py --quarter sfu --tiled --half-width --xroot lockup) against the generator's SFU reference
# (Plan.model, the tiled mapping model_tiled), plus the negative control and three tile mutants that must FAIL.
#   (1) regenerate from the die view (VARIANT, default r24p) and reproduce the committed rtl_tiled byte for byte;
#   (2) Verilator lint of the tile and the quarter with the REAL ot_su12_sfu lane RTL: no UNDRIVEN / PINMISSING /
#       IMPLICIT warning in the generated files (warnings inside the lane source are the lane's own);
#   (3) iverilog: every random die input word (held), the die output must settle to the reference: mismatches=0;
#   (4) must FAIL: quarter negative control (chain 0 broadcast bit 0 inverted), OT_SFU_TILE_MUT_ROT (forward rotation
#       RB+1), OT_SFU_TILE_MUT_TAP (the first stub-observed per-lane field bit from the next tap), OT_SFU_TILE_MUT_ACC (lane output bit 0
#       dropped from the accumulate).
#   bench_tiled.sh <outdir>   (run in the source root)   prints SFU_TILED_BENCH_PASS when every check holds
set -u; O=$1; mkdir -p $O; m=hfd_sfu; R=physical/hbm_accel_die_views/sfu/rtl_tiled
python3 tools/hbm_die_views.py --variant ${VARIANT:-r24p} ports --master $m --out $O/ports > /dev/null || { echo "ports_rc=1"; exit 1; }
python3 tools/hbm_hub_quarter_gen.py --quarter sfu --ports $O/ports/$m/ports.json --out $O/gen --tiled --half-width --xroot lockup \
  --nvec ${NVEC:-6} > $O/plan.log 2> $O/gen.err || { echo "gen_rc=1"; cat $O/gen.err; exit 1; }
: > $O/result.txt
ok=1
for f in $m.sv ${m}_neg.sv hfd_sfu_tile.sv tile/io_place.tcl tile/macro_place.tcl tile/tile.json macro_place.tcl; do
  if cmp -s $O/gen/$f $R/$f; then echo "repro $f ok" >> $O/result.txt; else echo "repro $f DIFFERS" >> $O/result.txt; ok=0; fi
done
LS="rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41/ot_hdc_fsqrt_c12.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv"
# warning names differ across Verilator releases: pass only the suppressions this release knows
VW=""; for w in DECLFILENAME UNUSED UNUSEDSIGNAL UNUSEDPARAM PINCONNECTEMPTY VARHIDDEN WIDTH WIDTHEXPAND WIDTHTRUNC SYNCASYNCNET UNOPTFLAT CASEINCOMPLETE BLKSEQ MULTIDRIVEN TIMESCALEMOD; do
  verilator --lint-only -Wno-$w --top-module x /dev/null 2>&1 | grep -q "Unknown warning" || VW="$VW -Wno-$w"; done
for top in hfd_sfu_tile $m; do
  verilator --lint-only -Wall $VW --top-module $top $( [ $top = $m ] && echo $O/gen/$m.sv ) $O/gen/hfd_sfu_tile.sv $LS > $O/lint_$top.log 2>&1
  nw=$(grep "%Warning-\(UNDRIVEN\|PINMISSING\|IMPLICIT\)" $O/lint_$top.log | grep -c "$O/gen/")
  ne=$(grep "%Error" $O/lint_$top.log | grep -vc "Exiting due to")
  echo "lint $top generated-file warnings=$nw errors=$ne" >> $O/result.txt
  [ "$nw" = 0 ] && [ "$ne" = 0 ] || ok=0
done
cd $O/gen
sim() {  # sim <tag> <rtl> [defines]: OT_RESULT line + rc
  local tag=$1 rtl=$2; shift 2
  iverilog -g2012 "$@" -o sim_$tag tb_$m.sv $rtl hfd_sfu_tile.sv ot_su12_sfu_simstub.sv && vvp -n sim_$tag > $tag.log 2>&1
  echo "$tag rc=$? $(grep OT_RESULT $tag.log)" >> ../result.txt
}
sim pos $m.sv
grep -q "^pos rc=0 .*mismatches=0" ../result.txt || ok=0
sim neg ${m}_neg.sv
sim mut_rot $m.sv -DOT_SFU_TILE_MUT_ROT
sim mut_tap $m.sv -DOT_SFU_TILE_MUT_TAP
sim mut_acc $m.sv -DOT_SFU_TILE_MUT_ACC
for t in neg mut_rot mut_tap mut_acc; do
  grep -q "^$t rc=[1-9].*mismatches=[1-9]" ../result.txt && echo "$t FAILS as required" >> ../result.txt || { echo "$t DID NOT FAIL" >> ../result.txt; ok=0; }
done
[ $ok = 1 ] && echo SFU_TILED_BENCH_PASS >> ../result.txt || echo SFU_TILED_BENCH_FAIL >> ../result.txt
cat ../result.txt
[ $ok = 1 ]
