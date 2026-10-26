#!/bin/bash
# TOK-FUNC-QW stage "ovl4u" (10-21): 4-user overlapping-segment (OVL) compute<->KV D2D pair, full F16 frame, on the RTL-only
# SOURCE ASSEMBLY (RUNROOT/src), Verilator 5.050.
#
#   stage_ovl4u.sh RUNROOT [--release-masters] [--die-netlist DIR]
#
# --release-masters (TOK-FUNC2-QW-OVL 10-21): the bench is rtl/test/qwen_split/run_d2d_ovl_mu_rel.sh + tb_d2d_ovl_mu_rel.sv
#   (fixtures RUNROOT/ovl4u/fx/rel, stage_link_fixtures.sh): the RELEASE D2D masters of the assembly, compute
#   qfd_d2d_static_ovl_sf7 (kit qfd_d2d_static_sf7w) <-> KV qkd_d2d_static_ovl_sfm3 #(NTX 3, SRAMV 2, FEG 1) (kit
#   qkd_d2d_static_ovl_sfm3), with their pin flops, recovery/boot, STATUS + KVN codecs, + ot_qwen_d2d_ovl_seq x2; PHY =
#   ot_qkvd_ucie_x64_phy_model (the only modelled leg).  NO end overlay: grade "RTL-functional (source assembly)".  Runs in
#   RUNROOT/ovl4u_rel (the DIAG path keeps RUNROOT/ovl4u); collect with run_tok_func_qw.sh --stage-dir ovl4u=ovl4u_rel.
#   Macro views: d2d_sram_1r1w_64x137_m1_r2c2_p288 (assembly) and ot_sram_1r1w_64x137_m1_r2c2_p192 (the sf7 SAFE5/7 store;
#   not in the assembly's physical/asap7_memory_macros_v2, staged from 545cdd4bc = the closed sf7w kit's view).
#
# Bench = existing rtl/test/qwen_split/run_d2d_ovl_mu.sh + tb_d2d_ovl_mu.sv (MU-D2D-OVL 10-19, branch codex/sysface-ovl-1019;
# bench files only, from RUNROOT/ovl4u/fx): ot_qwen_d2d_static x2 (OVL=1) + ot_qwen_d2d_ovl_seq x2 + crc/slot link/LLR/SRAM
# from the assembly, PHY = ot_qkvd_ucie_x64_phy_model (the only modelled leg).  Calendars compiled HERE by the assembly's
# compiler (python3 -m qwen_static_schedule.mu_d2d_ovl --kv-codec C --kv-prog [--mut M]) for codecs 1 and 2.
# Configs: pass (PASS: every C->K / K->C frame bit-exact against the compiled producer words), asbuilt_one_playhead,
# mut_collide, mut_slot, mut_user (FAIL).  Cycles (stage_link.collect.py ovl4u): frame H, tokens/frame per user,
# cycles/token per user, aggregate tok/s at 833 ps (1.2 GHz), frames C->K / K->C.
#
# --die-netlist DIR (closure hook): DIR/xq_stages.txt = the netlisted seam stages "C.../K..." of the closed compute + KV
#   dies (record_bundle_audit form, e.g. 2,2,2,3,2,2/11,11,9,9,9,9,9) -> passed as --stages to the compiler so the frame
#   is compiled for the closed seam; the link RTL itself stays source (the d2d end is a hard tile with its own LEC).
set -u
RUNROOT=$(readlink -f "$1"); shift
NET=""; REL=0
while [ $# -gt 0 ]; do case "$1" in --die-netlist) NET=$(readlink -f "$2"); shift 2;; --release-masters) REL=1; shift;;
  *) echo "bad arg $1"; exit 2;; esac; done
SRC=$RUNROOT/src; S=$RUNROOT/ovl4u; FX=$S/fx; HERE=$(dirname "$(readlink -f "$0")")
[ $REL = 1 ] && S=$RUNROOT/ovl4u_rel
T=$S/tree; mkdir -p "$S"
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$VERILATOR --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
[ -f "$FX/rtl/test/qwen_split/tb_d2d_ovl_mu.sv" ] || { echo "missing fixtures (stage_link_fixtures.sh)"; exit 2; }
RB=run_d2d_ovl_mu.sh; RFX=$FX
if [ $REL = 1 ]; then
  RB=run_d2d_ovl_mu_rel.sh; RFX=$FX/rel
  for f in rtl/test/qwen_split/run_d2d_ovl_mu_rel.sh rtl/test/qwen_split/tb_d2d_ovl_mu_rel.sv \
           physical/asap7_memory_macros_v2/ot_sram_1r1w_64x137_m1_r2c2_p192/ot_sram_1r1w_64x137_m1_r2c2_p192.v \
           physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p288/d2d_sram_1r1w_64x137_m1_r2c2_p288.v; do
    [ -f "$RFX/$f" ] || { echo "missing release fixture $RFX/$f (stage_link_fixtures.sh)"; exit 2; }; done
fi
GRADE="RTL-functional (source assembly)"; STG=()
# QC-TOK 10-24: compile the OVL frame for the bound seam (bound_r8 XDIE_DIE_STAGES), grade stays source assembly
[ -n "${OVL_STAGES:-}" ] && STG=(--stages "$OVL_STAGES")
if [ -n "$NET" ]; then [ -f "$NET/xq_stages.txt" ] || { echo "no $NET/xq_stages.txt"; exit 2; }; STG=(--stages "$(cat $NET/xq_stages.txt)"); GRADE="die-netlist"; fi
# overlay: rtl/physical/configs symlinked from src + fixtures; tools and results REAL files (the compiler resolves ROOT from
# its own path, so tools/qwen_static_schedule + tools/qwen_split must be real copies under the tree)
rm -rf "$T" "$S/runs"; mkdir -p "$T/physical" "$S/runs"
for d in rtl tools configs; do cp -as "$SRC/$d" "$T/"; done
rm -rf "$T/tools/qwen_static_schedule" "$T/tools/qwen_split"; cp -a "$SRC/tools/qwen_static_schedule" "$SRC/tools/qwen_split" "$T/tools/"
cp -as "$SRC/physical/." "$T/physical/"; cp -as "$FX/physical/." "$T/physical/"; cp -a "$FX/results" "$T/"
[ $REL = 1 ] && cp -as "$RFX/physical/." "$T/physical/"
TB=${RB/run_/tb_}; TB=${TB%.sh}.sv
for f in rtl/test/qwen_split/$RB rtl/test/qwen_split/$TB; do rm -f "$T/$f"; cp "$RFX/$f" "$T/$f"; done
cd "$T" || exit 3
# DUT gap (10-21): the bench drives ot_qwen_d2d_static_end #(.OVL(1)) (cal_start_rx / cal_seg_rx / cal_user_* / tx_user / rx_user).
# The assembly's ot_qwen_d2d_static.sv (9991e8715) has NO OVL form; its OVL-capable ends are the pin-copied safe forms
# (ot_qwen_d2d_static_end_sfm/sfm3, _s7) that this bench cannot drive.  Until a 4u bench on those forms exists, the OVL end
# file is overlaid from codex/sysface-ovl-1019 967c24eed (as on 10-19) -> stand-in, grade "DIAG (OVL end overlay)".
# --release-masters (10-21) is that bench: the release masters of the assembly, no overlay (DIAG path kept for comparison).
rm -f $S/ovl_overlay.txt $S/release_masters.txt
if [ $REL = 1 ]; then
  echo "qfd_d2d_static_ovl_sf7 <-> qkd_d2d_static_ovl_sfm3 (assembly $(cat $SRC/ASM_COMMIT 2>/dev/null)); bench $RB" > $S/release_masters.txt
elif ! grep -q 'cal_user_tx' rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv; then
  f=rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv; rm -f "$f"; cp "$FX/overlay/$f" "$f"
  echo "$f from codex/sysface-ovl-1019 967c24eed (sha $(sha256sum $f | cut -c1-12)): assembly end has no OVL form" > $S/ovl_overlay.txt
  [ -n "$NET" ] || GRADE="DIAG (OVL end overlay; rest source assembly)"
fi
# compiler fix (claude/tokfunc-qw-link-fix-1021 f98fd830f): c0f8097f3's mu_calendar ignores the attn_extra / att_windows that
# mu_d2d_ovl passes -> every compiled OVL frame collides.  Applied to the tree copy only when the source lacks it.
rm -f $S/compiler_patch.txt
if ! grep -q 'att_windows' tools/qwen_static_schedule/mu_calendar.py; then
  patch -p1 < "$FX/mu_calendar_attwin.patch" > $S/compiler_patch.log 2>&1 || { cat $S/compiler_patch.log; exit 2; }
  echo "tools/qwen_static_schedule/mu_calendar.py + f98fd830f (claude/tokfunc-qw-link-fix-1021: attn_extra/att_windows consumer)" > $S/compiler_patch.txt
fi
R=$S/runs; ALL=0
for c in 1 2; do
  for m in pass collide slot user; do
    mut=(); [ $m != pass ] && mut=(--mut $m)
    ( cd tools && python3 -m qwen_static_schedule.mu_d2d_ovl --out $R/cal_c$c/cal_$m --kv-codec $c --kv-prog "${mut[@]}" "${STG[@]}" ) > $R/cal_c${c}_$m.log 2>&1
    echo "cal codec$c $m rc=$?" | tee -a $R/cal.rc
  done
  ( JOBS=4 bash rtl/test/qwen_split/$RB $R/codec$c $R/cal_c$c > $R/codec$c.out 2>&1; echo "rc=$?" >> $R/codec$c.out ) &
done
wait
for c in 1 2; do echo "==== codec$c"; cat $R/codec$c.out; done
python3 "$HERE/stage_link.collect.py" ovl4u "$RUNROOT" --grade "$GRADE" --stage-dir "$(basename $S)"
