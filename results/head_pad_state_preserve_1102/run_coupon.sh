#!/usr/bin/env bash
# DH54-PAD successor runner (replaces the deliberately refusing 69812606f run_disabled.sh; that file is untouched).
# Host side (intel2). Every step runs in openroad/orfs:asap7lock with --memory 4g --cpus 1.
#   COUPON  = this directory (read-only in the container as /coupon); prep/ = git archive of the 69812606f packet
#   OUT     = output dir (container /out)
# Setup + run (11-02, intel2, ~2.5 min wall):
#   mkdir -p $C/prep && cp results/head_pad_state_preserve_1102/* $C/
#   git archive 69812606f results/qc_sc_red_diagnostics_1101/head_pad_state_preserve_prep | tar -x -C $C/prep --strip-components=3
#   cd $C && ./run_coupon.sh      (C=/srv/opentallas-scratch2/claude/dh54-pad; results in $C/out, summary out/RESULT.json)
set -euo pipefail
COUPON=${COUPON:-$(cd "$(dirname "$0")" && pwd)}
OUT=${OUT:-$COUPON/out}
IMG=${IMG:-openroad/orfs:asap7lock}
mkdir -p "$OUT"
DR=(docker run --rm --memory 4g --memory-swap 4g --cpus 1 --user "$(id -u):$(id -g)"
    -v "$COUPON":/coupon:ro -v "$COUPON/prep":/work:ro -v "$OUT":/out "$IMG")
docker image inspect "$IMG" --format '{{.Id}}' > "$OUT/image_id.txt"
"${DR[@]}" bash -c '/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -V; sha256sum /OpenROAD-flow-scripts/flow/scripts/synth.tcl /OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl /OpenROAD-flow-scripts/flow/scripts/synth_canonicalize.tcl /coupon/prep/synth.tcl /coupon/prep/synth_preamble.tcl /coupon/prep/synth_canonicalize.tcl /coupon/prep/ot_keep_regs.reference.tcl /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO_RVT_TT_nldm_211120.lib.gz,INVBUF_RVT_TT_nldm_220122.lib.gz,OA_RVT_TT_nldm_211120.lib.gz,SEQ_RVT_TT_nldm_220123.lib,SIMPLE_RVT_TT_nldm_211120.lib.gz}' > "$OUT/versions.txt"

# packet hook as shipped: expected to fail closed on its selector (recorded, not a synth run)
"${DR[@]}" bash /coupon/synth_one.sh m0_cellkeep_pkt 0 cellkeep_pkt > "$OUT/m0_cellkeep_pkt.status" 2>&1 && echo RAN >> "$OUT/m0_cellkeep_pkt.status" || echo "FAILED_CLOSED rc=$?" >> "$OUT/m0_cellkeep_pkt.status"
rm -rf "$OUT/m0_cellkeep_pkt/flow/objects"
# name mode hook   (hook: kit = kit SYNTH_CANONICALIZE_TCL ot_keep_regs; none = no hook; cellkeep = packet per-bit cell KEEP)
RUNS=("m0_kit 0 kit" "m1_nohook 1 none" "m1_kit 1 kit" "m0_cellkeep 0 cellkeep" "m2_kit 2 kit" "m3_kit 3 kit")
for r in "${RUNS[@]}"; do
  set -- $r
  "${DR[@]}" bash /coupon/synth_one.sh "$1" "$2" "$3"
  "${DR[@]}" bash -c "cd /tmp && python3 -I /coupon/formal_check.py --kind netlist --top head_pad_fragment --ref /coupon/ref_model.sv --tag $1 --outdir /out/formal /out/$1/flow/results/asap7/$1/base/1_2_yosys.v"
  "${DR[@]}" bash -c "ODB=/out/$1/flow/results/asap7/$1/base/1_synth.odb /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /coupon/odb_count.tcl 2>&1 | grep ODBCOUNT > /out/$1/odb_count.txt || true"
done
# fold localisation diagnostics (replay of synth.tcl stage order; opt_dff isolation)
for r in m0_kit m1_nohook m1_kit m0_cellkeep m2_kit m3_kit; do
  "${DR[@]}" bash -c "cd /tmp && /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -p 'read_rtlil /out/$r/flow/results/asap7/$r/base/1_1_yosys_canonicalize.rtlil; script /coupon/fold_trace.ys' > /out/$r/fold_trace.log 2>&1"
done
for r in m1_kit m0_cellkeep; do
  "${DR[@]}" bash -c "cd /tmp && /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -p 'read_rtlil /out/$r/flow/results/asap7/$r/base/1_1_yosys_canonicalize.rtlil; script /coupon/optdff_probe.ys' > /out/$r/optdff_probe.log 2>&1"
done
# RTL controls: checker positive controls (source fragment modes, native model) and the 4 mutants (must REJECT)
for m in 0 1 2 3; do
  F=/coupon/prep/pad_fragment.sv; [ $m = 3 ] && F="$F /coupon/prep/native_ff_model.sv"
  "${DR[@]}" bash -c "cd /tmp && python3 -I /coupon/formal_check.py --kind rtl --top head_pad_fragment --param PRESERVE_MODE=$m --ref /coupon/ref_model.sv --tag rtl_mode$m --outdir /out/formal $F"
done
for m in 0 1 2 3; do
  "${DR[@]}" bash -c "cd /tmp && python3 -I /coupon/formal_check.py --kind rtl --top head_pad_fragment_mutant --param MUT=$m --ref /coupon/ref_model.sv --tag rtl_mutant$m --outdir /out/formal /coupon/prep/fragment_mutants.sv"
done
"${DR[@]}" python3 -I /coupon/summarize.py /out /out/RESULT.json
