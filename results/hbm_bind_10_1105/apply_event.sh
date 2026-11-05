#!/bin/bash
# HBM-BIND-10 C-form plan event (C row form + B0/b0l/pair leaf + hub<->sm endpoint reuse + L29_i +69.168 + spb0->root),
# applied as a per-item delta on whatever main d44v is when it runs. Run from a repo worktree root.
# Prints every conflict (an item a later event also changed); resolve those by hand before commit.
# Known overlap with DIE-HBM-74 ev74: q_sm0 L29_i window (same +69.168 value) and q_su01 L29x1 (C deletes it).
set -euo pipefail
F=results/hbm_bind_10_1105; D=physical/die_plan/hbm/plan_of_record/d44v; T=$(mktemp -d)
gunzip -c $D/die_plan.json.gz > $T/base.json
python3 -I $F/plan_delta.py apply $T/base.json $F/delta_714_k13f.json.gz $T/new.json | tee $T/apply.log
gzip -n -9 -c $T/new.json > $D/die_plan.json.gz
s=$(sha256sum $T/new.json | cut -d" " -f1); sed -i "s/^[0-9a-f]\{64\}  die_plan.json$/$s  die_plan.json/" $D/SHA256SUMS
grep -q "$s  die_plan.json" $D/SHA256SUMS && echo "SHA256SUMS die_plan.json = $s"
grep -c CONFLICT $T/apply.log || true
