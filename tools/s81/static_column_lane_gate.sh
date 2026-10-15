#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../.."
out=${1:?output directory required};mkdir -p "$out"
sources=(rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_lane.sv rtl/dsrom_sys/s81_die_bind/test/tb_static_column_lane.sv)
for phase in 1 2 4 6 8 9;do
  iverilog -g2012 -DDSFD_PQ_STATIC_X2 -s tb_static_column_lane -Ptb_static_column_lane.PHASE="$phase" -o "$out/sim" "${sources[@]}"
  vvp "$out/sim"
done
for stages in 0 3;do
  iverilog -g2012 -DDSFD_PQ_STATIC_X2 -s tb_static_column_lane -Ptb_static_column_lane.STAGES="$stages" -o "$out/sim" "${sources[@]}"
  vvp "$out/sim"
done
for mut in OT_S81_STATIC_COLUMN_MUT_SWAP OT_S81_STATIC_CROSS_MUT_OFFSET DSFD_PQ_X2_MUT_SWAP;do
  iverilog -g2012 -DDSFD_PQ_STATIC_X2 -D"$mut" -s tb_static_column_lane -o "$out/sim" "${sources[@]}"
  if vvp "$out/sim" > "$out/$mut.log" 2>&1;then echo "mutant escaped: $mut" >&2;exit 1;fi
  rg 'composed mismatch' "$out/$mut.log"
done
echo 'STATIC_COLUMN_LANE_GATE PASS actual encoder, crossing, packed stages, BF decode; three mutants rejected'
