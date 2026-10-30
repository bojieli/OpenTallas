#!/usr/bin/env bash
set -u
R=/srv/opentallas-scratch2/claude/codex-hbm-bind-2249
TL=/srv/opentallas-scratch2/claude/wt/codex-hbm-bind-2249/tools/die_plan
P=/srv/opentallas-scratch2/claude/die-hbm-29/plan/d29d
python3 "$R/swap102_event_fixed.py" "$TL" "$P" "$R/swap102_variant.json" "$R/swap102" --max-hops 8 > "$R/swap102_event.log" 2>&1
rc=$?;echo "$rc" > "$R/swap102_event.rc";[ "$rc" -eq 0 ] || exit "$rc"
python3 "$R/order_fix.py" "$TL" "$R/swap102/die_plan.json" > "$R/swap102_post.log" 2>&1
rc=$?;[ "$rc" -eq 0 ] || exit "$rc"
python3 "$R/post_fix2.py" "$R/swap102/die_plan.json" >> "$R/swap102_post.log" 2>&1
rc=$?;[ "$rc" -eq 0 ] || exit "$rc"
python3 "$R/post_fix3.py" "$TL" "$R/swap102/die_plan.json" >> "$R/swap102_post.log" 2>&1
rc=$?;[ "$rc" -eq 0 ] || exit "$rc"
python3 "$TL/gen.py" latency "$R/swap102/die_plan.json" --inplace --out "$R/lat_swap102" > "$R/swap102_latency.log" 2>&1
rc=$?;[ "$rc" -eq 0 ] || exit "$rc"
python3 "$TL/check.py" "$R/swap102/die_plan.json" > "$R/swap102_g0.log" 2>&1
echo $? > "$R/swap102_g0.rc"
python3 "$TL/check.py" "$R/swap102/die_plan.json" --completeness > "$R/swap102_g0c.log" 2>&1
echo $? > "$R/swap102_g0c.rc"
