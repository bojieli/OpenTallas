#!/bin/bash
# beat_bench.sh <outdir> [base|baseimm|muttree|mutcoef|mutpostlast|mutnormimm|mutpre] [BEAT] [L0|L2]  (cwd = repo root): S81-SLICE beat-leaf bench (vp + vn + vq)
# on the 1M token's real layer chain (su_cases).  base must PASS; the mutants must FAIL.  Exit 0 = the expected verdict.
# S81SL_VQ_XMEM=1|2 builds vq with its SRAM-ring x wait line (ot_s81sl_vq AQ_XMEM; the kit sets 2).
# baseimm = base with the legacy op 5 NORM (hc_pre in the imm) instead of op 7 NORMR (hc_pre = the G-unit's leaf row R);
# mutpostlast / mutnormimm = vp RTL mutants (old POST row order / NORMR ignoring the row), must FAIL.
# A 5th argument 'raw' reports a mutant's own verdict instead (prints SLBEAT, exit 1 on FAIL: an expect=fail bench).
# S81-PLAN R3: S81SL_CST="-GCS_HI_D=2 ... +define+OT_S81SL_CST_MUT_*" = leaf station depths / station mutants
set -u; O=$1; M=${2:-base}; B=${3:-37}; L=${4:-L0}; mkdir -p $O/run
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
CASES=${S81_SU_CASES:-tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl}
python3 tools/s81_slice/leaf_gold.py $CASES $B $O/run $L > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; tail -5 $O/gold.log; exit 4; }
DEF=""; [ "$M" = muttree ] && DEF="+define+OT_S81SL_MUT_TREE"; [ "$M" = mutcoef ] && DEF="+define+OT_S81SL_TB_MUT_COEF"; [ "$M" = mutpre ] && DEF="+define+OT_S81SL_MUT_PRESTALE"
[ "$M" = mutpostlast ] && DEF="+define+OT_S81SL_VP_MUT_POSTLAST"; [ "$M" = mutnormimm ] && DEF="+define+OT_S81SL_VP_MUT_NORMIMM"
NR=1; [ "$M" = baseimm ] && NR=0
MACV="physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
srcs="$(sort -u physical/hbm_norm_split_20261008/sources.f | tr '\n' ' ') rtl/hdc/v41x/ot_dsrom_su_add6.sv $MACV rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_beat.sv"
/usr/bin/time -v -o $O/time.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD ${S81SL_CST:-} $DEF -GBEAT=$B -GNORMR=$NR -GVQ_XMEM=${S81SL_VQ_XMEM:-0} --top-module tb_s81sl_beat -Mdir $O/obj $srcs \
  --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
(cd $O/run && ../obj/Vtb_s81sl_beat > ../run.log 2>&1)
grep -E "MISMATCH" $O/run.log | head -12; grep -E "^SLBEAT" $O/run.log   # SLBEAT apart: >13 mismatches hid it behind head (s81sl_vq a58a22ede)
if [ "$M" = base ] || [ "$M" = baseimm ]; then grep -q '^PASS' $O/run.log && { echo "PASS beat $M B=$B $L"; exit 0; }; echo "FAIL beat"; exit 1; fi
[ "${5:-}" = raw ] && { grep -q '^PASS' $O/run.log && exit 0; exit 1; }
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
