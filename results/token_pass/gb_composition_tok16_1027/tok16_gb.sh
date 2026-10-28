#!/bin/bash
# TOK-ALL-16 GB composition: fresh extraction on the tok16 (hard-params restored) candidate manifest, vectors, bench.
set -euo pipefail
SRC=/srv/opentallas-scratch2/claude/wt/claude-tok15-gb-1027
O=/srv/opentallas-scratch2/claude/tok16-gb
export GB_MANIFEST=physical/die_plan/s81/bind/asbuilt_b178_gb_image_candidate_tok16.json
cd "$SRC"
mkdir -p "$O/asb_sched"
for mv in col_h10:x col_h10:nx col_h9:x col_h9:nx; do
  m=${mv%%:*}; v=${mv##*:}
  python3 tools/s81_dv/frame_schedule_asb.py --master $m --var $v --manifest "$GB_MANIFEST" \
     --out "$O/ex_${m}_$v" --work "$O/ex_${m}_$v/work" > "$O/ex_${m}_$v.log" 2>&1 &
done
wait
for mv in col_h10:x col_h10:nx col_h9:x col_h9:nx; do m=${mv%%:*}; v=${mv##*:}
  head -1 "$O/ex_${m}_$v.log"; cp "$O/ex_${m}_$v"/*.json "$O/asb_sched/"; done
mkdir -p "$O/asb_sched/work"; cp "$O/ex_col_h10_x/work/col_h10_l4_lp_asb_x.ys" "$O/asb_sched/work/"
bash tools/s81_dv/tokfunc/gen_dense_gb_vectors.sh "$SRC" /srv/opentallas-scratch2/claude/tok-ds-12-1027/veh/tree_b178 \
   /srv/opentallas-scratch2/claude/tok15-gb/fixtures/L0 "$O/asb_sched" "$O/vec" > "$O/gen.log" 2>&1
OT_XS_ASB_SCHEDULE_DIR="$O/asb_sched" J=16 bash tools/s81_dv/tokfunc/run_dense_xs_cap_gb.sh "$O/run1" "$O/vec/vec_pos" "$O/vec/vec_oldq" "$O/vec/vec_wrongimg"
