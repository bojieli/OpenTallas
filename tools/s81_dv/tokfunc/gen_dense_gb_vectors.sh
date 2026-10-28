#!/bin/bash
# TOK-ALL-15 (10-27): vectors for run_dense_xs_cap_gb.sh, from the selected die_b178 tree + L0 checkpoint fixture.
#   gen_dense_gb_vectors.sh SRC TREE FIXTURES SCHED_DIR OUT
# SRC = this worktree (selected source root), TREE = mk_vehicle_current.sh tree_b178 (die.v == die_b178.v),
# SCHED_DIR = fresh frame_schedule_asb.py extractions of all four as-built masters on the GB image candidate manifest.
# Writes OUT/capture-map.json, OUT/vec_pos (native Q advance1), OUT/vec_oldq (legacy Q launch control),
# OUT/vec_wrongimg (lower_xs --mutant swap images loaded under the actual INSTANCE names).
set -euo pipefail
SRC=$(realpath "$1"); TREE=$(realpath "$2"); FX=$(realpath "$3"); SCHED=$(realpath "$4"); OUT=$(realpath -m "$5")
FRAME=${GB_FRAME:-u_f_0L01}; SLICE=${GB_SLICE:-u_s_0S}
cd "$SRC"
mkdir -p "$OUT"
export OT_XS_ASB_SCHEDULE_DIR=$SCHED
export OT_S81_SELECTED_ASBUILT_MANIFEST=${GB_MANIFEST:-physical/die_plan/s81/bind/asbuilt_b178_gb_image_candidate_1450.json}
export OT_S81_SELECTED_SOURCE_ROOT=$SRC
export OT_S81_SELECTED_CHILD_FILES=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv
export OT_XS_GB_PROVIDER_UNDER_TEST=1 OT_XS_Q_CPR=1
(cd tools/s81_dv/layer_prog && python3 aproj_native_pair_map.py --tree "$TREE" --fixtures "$FX" --out "$OUT/capture-map.json")
export OT_XS_APROJ_TOPO=1 OT_XS_APROJ_ALIGN4=1 OT_XS_APROJ_RANK_TAGS=1 OT_XS_DENSE_SPLIT2=B OT_XS_APROJ_CAP_PLAN=1
for v in pos wrongimg; do
  M=(); [ $v = wrongimg ] && M=(--mutant swap)
  python3 tools/s81_dv/layer_prog/lower_xs.py gen --die-src "$TREE" --fixtures "$FX" --slice $SLICE --frame $FRAME \
    --out "$OUT/vec_$v" --cycles 4000 "${M[@]}"
done
# lower_xs swaps only the bench-name ('f') copies; load them under the actual INSTANCE names too
(cd "$OUT/vec_wrongimg" && for f in f_*; do cp "$f" "$FRAME${f#f}"; done)
rm -rf "$OUT/vec_oldq"; cp -a "$OUT/vec_pos" "$OUT/vec_oldq"
for v in pos:native_advance1 oldq:old wrongimg:native_advance1; do
  python3 tools/s81_dv/tokfunc/dense_xs_program.py --vectors "$OUT/vec_${v%%:*}" --capture-map "$OUT/capture-map.json" \
    --die-master col_h10_l4_lp_asb_x --q-calendar ${v##*:}
done
