#!/bin/sh
# S81 latency table of record with the R8 landed-bundle pads priced (COORD 10-24 18:55).  Run from the repo root.
# Bus groups = BINDER4 b3r8 as-built bind (plan v4.7b; bound depths rebased onto this plan by lane), options = the
# S81-P9-R8EQ v4.8 checks (r8eq_v48_checks.json, landed_rule_keep: over-margin bundles keep per-lane pads).
set -e
D=physical/die_plan/s81
python3 tools/die_plan/gen.py latency $D/die_plan.json --out $D/lat \
  --groups $D/lat/inputs/bus_groups_b3r8_v47b.json.gz --rebase-bind $D/lat/inputs/bind_latency_b3r8_v47b.json.gz \
  --replica type --bus leaf --exempt '(?i)(^|_)(fault|flt)(_o|_q)?$' \
  --landed '^(x|xo)_[WE][0-5]_' --landed '^xring__' --landed '^sid_s_' --landed-over-margin keep --fold-r8
