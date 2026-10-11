#!/bin/bash
# hgi-1010/att: R25 ATT transaction bench.   run_att_r25.sh <out dir> <set> [NA]   (from the source snapshot root)
#   pos   : vectors <set>, random svc order (seed 1, 2) + in-order, NA tile rows             -> ATT_R25 PASS each
#   mutants (each must FAIL): B1 partner duplicates (OT_ATTN_MUT_KVIB_PARTNER), B2 rows by arrival not tag
#     (OT_ATT_STG_MUT_TAG), B3 two entries on one tile row (VEH 3), B4 PV not transposed (OT_ATT_STG_MUT_TP),
#     KQ credit on arrival (OT_ATT_STG_MUT_KQ), bank (OT_ATT_STG_MUT_BANK), slice order (OT_ATT_R25_MUT_KQORD).
# Env: MUTS="..." to choose mutants (default all), POS=0 to skip the positive runs.  Verilator 5.050.
set -u
O=$1; SET=$2; NA=${3:-4}; mkdir -p $O
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 tools/hgi_att_r25_vectors.py --out $O/vec --set $SET --na $NA > $O/vec.log 2>&1 || { echo "vectors FAIL"; exit 2; }
SRC="rtl/hbm_accel/generic/att/tb/tb_hgi_att_r25.sv rtl/hbm_accel/generic/att/ot_hgi_att_r25.sv rtl/hbm_accel/generic/att/ot_hgi_att_stager.sv rtl/common/ot_fwd_link_stage.sv rtl/hdc/v41x/ot_hdc_v41x_attn_die_half_b.sv rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv rtl/hdc/v41x/ot_hdc_v41x_attn_bank.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m6h1r.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m8_phys.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_cg.sv rtl/hbm_accel/cg/ot_cg_tile.sv rtl/test/hdc_v41_harness.cpp"
build() { local t=$1; shift
  $V --cc --exe --build --timing -j ${J:-8} -O1 -CFLAGS -O1 -MAKEFLAGS OPT_SLOW=-O0 -Wno-fatal -Wno-WIDTH -Wno-UNUSED \
     -Wno-TIMESCALEMOD -Wno-PINMISSING -Wno-MULTIDRIVEN -Wno-BLKANDNBLK --top-module tb_hgi_att_r25 --prefix Vtb \
     -GNA=$NA -Mdir $O/$t "$@" $SRC > $O/build_$t.log 2>&1; }
sim() { local t=$1 b=$2; shift 2; $O/$b/Vtb +vec=$O/vec "$@" > $O/$t.log 2>&1; echo "$t rc=$? $(grep -h 'ATT_R25 \(PASS\|FAIL\)' $O/$t.log | tail -1)" >> $O/summary.txt; }
: > $O/summary.txt
MUTS=${MUTS-"B1 B2 B3 B4 KQ BANK KQORD"}
declare -A D=([B1]=-DOT_ATTN_MUT_KVIB_PARTNER [B2]=-DOT_ATT_STG_MUT_TAG [B3]=-GVEH=3 [B4]=-DOT_ATT_STG_MUT_TP [KQ]=-DOT_ATT_STG_MUT_KQ [BANK]=-DOT_ATT_STG_MUT_BANK [KQORD]=-DOT_ATT_R25_MUT_KQORD)
if [ "${POS:-1}" = 1 ]; then build pos & fi
for m in $MUTS; do build m_$m ${D[$m]} & done
wait
if [ "${POS:-1}" = 1 ]; then
  sim pos_s1 pos +seed=1 & sim pos_s2 pos +seed=2 & sim pos_in pos +inorder & wait
fi
for m in $MUTS; do sim mut_$m m_$m +seed=1 & done; wait
cat $O/summary.txt
rc=0
for t in pos_s1 pos_s2 pos_in; do [ "${POS:-1}" = 1 ] || break; grep -q "^$t rc=0 ATT_R25 PASS" $O/summary.txt || rc=1; done
for m in $MUTS; do grep -q "^mut_$m .*ATT_R25 PASS" $O/summary.txt && { echo "MUTANT NOT CAUGHT $m"; rc=1; }; done
echo "overall rc=$rc" | tee -a $O/summary.txt; exit $rc
