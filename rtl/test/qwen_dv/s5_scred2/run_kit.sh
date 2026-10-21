#!/usr/bin/env bash
# Kit benches (closure daemon / fleet, Verilator 5.050): the KIT netlist (bounded constructor output, leaf wrapper) vs the
# ORIGINAL leaf (qfd_dv_s5_red / qfd_dv_s5_sc text from qfd_dv_s5_leaves.sv) at the priced offsets.
# Usage: run_kit.sh OUT red|sc eq|mut [CFG]   (mut: the real mutant netlist is rebuilt here by construct.sh from the RTL)
# CFG = LA LM digits of the kit netlist (default 79); offsets follow the priced formulas (QW-S5-SCRED 10-21).
set -euo pipefail
O=$1; K=$2; M=$3; CFG=${4:-79}; LA=${CFG:0:1}; LM=${CFG:1:1}; mkdir -p "$O"
ROFF=$(( (LM-3) + 11*(LA-3) + 2 )); SDT=$(( 5*(LA-3) )); SDR=$(( 5*(LA-3) + (LM-3) + (LA-3) + 3*(3*(LM-3) + (LA-3)) ))
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version | tee "$O/verilator_version.txt" | grep -q 5.050
python3 rtl/test/qwen_dv/s5_scred2/extract_ref.py rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv "$O/ref.sv"
HDC="rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv"
COM="rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv rtl/qwen_dv/s5/qfd_dv_s5_red2.sv rtl/qwen_dv/s5/qfd_dv_s5_red_ring32.sv rtl/qwen_dv/qfd_dv_reset_tree.sv $HDC"
N=qfd_dv_s5_${K}2_k$CFG
NET="rtl/qwen_dv/s5/$N.sv rtl/qwen_dv/s5/${N}_helpers.sv"
DEF=()
if [[ $M == mut ]]; then
  MUTDEF=-DOT_S5_RED2_MUT; EXTRA=""; [[ $K == sc ]] && { MUTDEF=-DOT_S5_SC2_MUT; EXTRA="rtl/qwen_dv/s5/qfd_dv_s5_sc2.sv rtl/qwen_dv/qfd_dv_scalar2.sv"; }
  # sc2 kit netlists are built with --reuse-copies (QW-S5-SCRED); the mutant must be constructed the same way
  [[ $K == sc ]] && export CFLAGS="--load-cap 8 --transparent-inverters --retain-mux --shared-helpers --retain-keep --reuse-copies"
  PFX=qfd_${K:0:1}2_ bash rtl/test/qwen_dv/s5_scred2/construct.sh "$O/mutnet" qfd_dv_s5_${K}2 ${N}_mut "-set LA $LA -set LM $LM" "$MUTDEF" $EXTRA $COM
  NET="$O/mutnet/${N}_mut.sv $O/mutnet/${N}_mut_helpers.sv"; DEF=(+define+OT_S5_SCRED2_MUT_NETLIST)
fi
if [[ $K == red ]]; then
  TB=rtl/test/qwen_dv/s5_scred2/tb_red2.sv; T=tb_red2; DM=(+define+DUTMOD=qfd_dv_s5_red2_leaf +define+REFMOD=ref_s5_red +define+OFF=$ROFF +define+RDOFF=2)
  ARGS=(+seed=7 +segs=3000); PASS='RED2_EQ PASS'; FAIL='RED2_EQ FAIL'; LEAF=rtl/qwen_dv/s5/qfd_dv_s5_red2_leaf.sv; RTLX=""
else
  TB=rtl/test/qwen_dv/s5_scred2/tb_sc2.sv; T=tb_sc2; DM=(+define+DUTMOD=qfd_dv_s5_sc2_leaf +define+REFMOD=ref_s5_sc +define+OFF0=2 +define+AMO=2 +define+DT=$SDT +define+DR=$SDR)
  ARGS=(+seed=7 +rounds=40); PASS='SC2_EQ PASS'; FAIL='SC2_EQ FAIL'; LEAF=rtl/qwen_dv/s5/qfd_dv_s5_sc2_leaf.sv; RTLX=rtl/qwen_dv/qfd_dv_scalar2.sv
fi
"$V" --binary --timing -O1 -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign unique --x-initial unique \
  "${DEF[@]}" "${DM[@]}" --top-module $T "$O/ref.sv" $LEAF $NET $RTLX $HDC $TB -Mdir "$O/obj" > "$O/build.log" 2>&1
set +e; "$O/obj/V$T" "${ARGS[@]}" +verilator+seed+7 +verilator+rand+reset+2 > "$O/run.log" 2>&1; rc=$?; set -e
cat "$O/run.log" | grep -v '^- ' | tail -6
if [[ $M == eq ]]; then [[ $rc == 0 ]] && grep -q "$PASS" "$O/run.log"; else [[ $rc != 0 ]] && grep -q "$FAIL" "$O/run.log"; fi
