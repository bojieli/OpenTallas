#!/bin/bash
# HBM-CONS-2/KSH d44v part 56 replay, from the repo root of a checkout of the base commit with the RTL commit in history:
#   results/die_hbm_1104/reform_b/split_p56/replay_p56.sh RTL_COMMIT WORKDIR
set -eu; export PYTHONDONTWRITEBYTECODE=1
Q=results/die_hbm_1104/reform_b/split_p56; D=physical/die_plan/hbm/plan_of_record/d44v; RC=${1:?rtl commit}; W=${2:?new work dir}
rm -rf "$W"; mkdir -p "$W"; cp -a $D "$W/base"; find "$W/base" -name '*.gz' -exec gunzip -f {} +
[ -f "$W/base/split_event.json" ] && cp "$W/base/split_event.json" "$W/split_event.base.json"; cp -a "$W/base" "$W/new"
python3 -I results/die_hbm_1103/reform/mk_split.py "$W/new" $Q/split_p56.json $Q | tail -2 | cut -c1-240
python3 -I results/die_hbm_1103/reform/package.py "$W/new" "$W/base" $D | tail -1
python3 -I $Q/fin_p56.py . "$RC" "$W/split_event.base.json"
