#!/bin/bash
# QC s29 R8 = derive + deliberate pin (pin_r8_v2.py, DIE-QC-102). Never run a plain land_r8_derive.py derive for QC s29:
# it silently drops the 894 su-lane pins + the st_a->ctl r_v pad and the die still binds 0.
# usage: qc_r8_pinned.sh derive|check PLAN BUS_GROUPS TABLE [LIKE]   (PRE/EXTRA via env, defaults = the s29 pin)
set -eu; H=$(cd "$(dirname "$0")" && pwd); R=$H/../..
PRE=${R8_PIN_PRE:-$R/physical/die_plan/qwen_compute/qc_start_1106/runtime/zz_r8_s29q101O_g0.json.gz}; EXTRA=${R8_PIN_EXTRA:-0}
m=$1; PL=$2; BG=$3; T=$4
if [ "$m" = derive ]; then exec python3 -I $H/land_r8_derive.py derive "$PL" "$BG" --like "${5:-$T}" --out "$T" --pin-pre "$PRE" --pin-extra "$EXTRA"
else exec python3 -I $H/land_r8_derive.py check "$PL" "$BG" --table "$T" --pin-pre "$PRE" --pin-extra "$EXTRA"; fi
