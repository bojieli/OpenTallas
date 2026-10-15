#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../.."
out=${1:?output directory required};mkdir -p "$out"
sources=(rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress.sv rtl/dsrom_sys/s81_die_bind/test/tb_static_column_ingress.sv)
for phase in 1 4 6 9;do for trunk in 3 17;do
  iverilog -g2012 -s tb_static_column_ingress -Ptb_static_column_ingress.PHASE="$phase" -Ptb_static_column_ingress.TRUNK="$trunk" -o "$out/sim" "${sources[@]}"
  vvp "$out/sim"
done;done
iverilog -g2012 -DOT_S81_STATIC_CROSS_MUT_OFFSET -s tb_static_column_ingress -o "$out/sim" "${sources[@]}"
if vvp "$out/sim" > "$out/mut.log" 2>&1;then echo 'ingress offset mutant escaped' >&2;exit 1;fi
grep -E 'wrong first source epoch|wrong fixed edge|mismatch' "$out/mut.log"
echo 'STATIC_COLUMN_INGRESS_GATE PASS exact first epoch and every pin edge, variable trunk reset delay; mutant rejected'
