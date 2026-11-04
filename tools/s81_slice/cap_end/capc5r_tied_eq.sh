#!/bin/bash
# DIE-S81-53/CAPEND (11-04): capc5r_tied_eq.sh OUTDIR (repo root, on the fleet, never on the coordinator host).
# Lockstep of the tied plan master ot_s81sl_capc5r vs ot_s81sl_capc5r_w3 / _e6 (tb_capc5r_tied_eq.sv), random stimulus, N edges per run:
#   master form  base  no define
#                rf1   -DOT_S81_CAP_RT_RF1 -DOT_S81_CAP_RT_FACE_REGS (the master + its cap_rt preprocessed under those defines and
#                      renamed _rfx, so the variants keep their own pre-RF1 cap_rt in the same compile)
#                rf1ol rf1 + -DOT_S81_CAPC5R_OLATCH (+ -DOT_S81_CAP_RT_RF1_NOLAT, no double latch): out-face at the falling edge
# Then the 10-25 real-shape bench tb_capc5r_end_eq (cap_model.py real/random streams through the real die return chain), base form.
# Exit 0 iff every CMUT 0 run PASSES and every mutant FAILS.  env N (default 200000), SEEDS (default "1 2"), J.
set -u; O=$1; mkdir -p "$O"; N=${N:-200000}; SEEDS=${SEEDS:-1}
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
S=rtl/dsrom_sys/s81_dv/slice; T=tools/s81_slice/cap_end
COMMON="rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/hdc/ot_hdc_cg.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv
 $S/ot_s81sl_cap_tr.sv $S/ot_s81sl_cap_ld.sv $S/ot_s81sl_cap_ed.sv $S/ot_s81sl_cap_rt.sv $S/cap_end/ot_s81_retn_fwd.sv $S/cap_end/ot_s81sl_cap_trn.sv
 $S/cap_end/ot_s81sl_cap_rt_w.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_rst_copy.sv
 $S/lp/ot_s81sl_capc5r_w3.sv $S/lp/ot_s81sl_capc5r_e6.sv"
FLAGS="--binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --build-jobs ${J:-4}"
RENAME='s/\b(ot_s81sl_cap_rt|ot_s81sl_cap_grp|ot_s81sl_cap_grp_rf1|ot_s81sl_cap_rt_retn|ot_s81_fadd_pipe|ot_s81sl_cap_rt_olat|ot_s81sl_cap_rt_face_raw|ot_s81sl_cap_rt_face_reset|ot_s81sl_capc5r|ot_s81sl_capc5r_olat)\b/\1_rfx/g'
rc=0
form_srcs() {   # form -> REFDEF, REFSRC
  case $1 in
    base) REFDEF=""; REFSRC="$S/lp/ot_s81sl_capc5r.sv";;
    *) D="-DOT_S81_CAP_RT_RF1 -DOT_S81_CAP_RT_FACE_REGS"; [ "$1" = rf1ol ] && D="$D -DOT_S81_CAPC5R_OLATCH -DOT_S81_CAP_RT_RF1_NOLAT"
       $V -E -P $D $S/ot_s81sl_cap_rt.sv | sed -E "$RENAME" > "$O/ref_cap_rt_$1.sv" && $V -E -P $D $S/lp/ot_s81sl_capc5r.sv | sed -E "$RENAME" > "$O/ref_capc5r_$1.sv" \
         || { echo "PREPROCESS_FAILED $1"; exit 3; }
       REFDEF="-DCAPC5R_REF=ot_s81sl_capc5r_rfx"; REFSRC="$O/ref_cap_rt_$1.sv $O/ref_capc5r_$1.sv";;
  esac
}
for form in base rf1 rf1ol; do
  form_srcs $form
  for NL in 3 6; do for M in 0 1 2 3; do
    [ $M != 0 ] && [ $form != base ] && [ $M != 1 ] && continue    # all mutants on base; lane-tied mutant on the RF1 forms too
    B=$O/obj_${form}_${NL}_$M
    $V $FLAGS $REFDEF -GNL=$NL -GN=$N -GCMUT=$M --top-module tb_capc5r_tied_eq -Mdir "$B" $COMMON $REFSRC $T/tb_capc5r_tied_eq.sv > "$B.build.log" 2>&1 \
      || { echo "BUILD_FAILED $form NL=$NL M=$M"; grep -m6 "%Error" "$B.build.log"; exit 3; }
    for s in $SEEDS; do
      [ $M != 0 ] && [ "$s" != "${SEEDS%% *}" ] && continue
      "$B/Vtb_capc5r_tied_eq" > "$O/run_${form}_${NL}_${M}_$s.log" 2>&1
      l=$(grep -h "CAPC5R_TIED_EQ" "$O/run_${form}_${NL}_${M}_$s.log"); echo "$form $l"
      if [ $M = 0 ]; then echo "$l" | grep -q " PASS " || rc=1; else echo "$l" | grep -q " FAIL " || { echo "MUTANT_NOT_CAUGHT"; rc=1; }; fi
    done
  done; done
done
# seed 2: rebuild with SEED parameter (base and rf1ol, unmutated)
for form in base rf1ol; do form_srcs $form; for NL in 3 6; do
  B=$O/obj_s2_${form}_$NL
  $V $FLAGS $REFDEF -GNL=$NL -GN=$N -GSEED=2 --top-module tb_capc5r_tied_eq -Mdir "$B" $COMMON $REFSRC $T/tb_capc5r_tied_eq.sv > "$B.build.log" 2>&1 || { echo "BUILD_FAILED seed2 $form $NL"; exit 3; }
  "$B/Vtb_capc5r_tied_eq" > "$O/run_s2_${form}_$NL.log" 2>&1; l=$(grep -h CAPC5R_TIED_EQ "$O/run_s2_${form}_$NL.log"); echo "seed2 $form $l"; echo "$l" | grep -q " PASS " || rc=1
done; done
# real-shape streams through the die return chain (10-25 bench, base form)
RS="$COMMON $S/lp/ot_s81sl_capc5r.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv
 rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross_hr.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress_hr.sv rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_crs.sv $T/tb_capc5r_end_eq.sv"
for NL in 3 6; do
  B=$O/obj_real_$NL
  $V $FLAGS -GNL=$NL --top-module tb_capc5r_end_eq -Mdir "$B" $RS > "$B.build.log" 2>&1 || { echo "BUILD_FAILED real NL=$NL"; grep -m6 "%Error" "$B.build.log"; rc=1; continue; }
  for v in real:1 real:2 random:1 random:2 random:3; do
    c=${v%:*}; s=${v#*:}; VD=$O/vec_${c}_$s
    [ -f "$VD/T" ] || python3 tools/s81_slice/cap_model.py gen --case $c --seed $s --out "$VD" > "$O/gen_${c}_$s.log" 2>&1 || { echo "GEN_FAILED $v"; rc=1; continue; }
    "$B/Vtb_capc5r_end_eq" +DIR="$VD" +T=$(cat "$VD/T") > "$O/real_${NL}_${c}_$s.log" 2>&1
    l=$(grep -h END_EQ "$O/real_${NL}_${c}_$s.log"); echo "$c:$s $l"; echo "$l" | grep -q PASS || rc=1
  done
done
echo "CAPC5R_TIED_EQ_EXIT $rc"; exit $rc
