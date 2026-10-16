#!/usr/bin/env bash
set -euo pipefail
MODE=${1:?pass|mut_bypass};OUT=${2:?output};mkdir -p "$OUT"
R=$(cd "$(dirname "$0")/../.."&&pwd);ARGS=()
case "$MODE" in pass);;mut_bypass)ARGS=(-DOT_CFIFO_RETURN_MUT_BYPASS);;*)exit 2;;esac
iverilog -g2012 "${ARGS[@]}" -s tb_cfifo_return_launch -o "$OUT/sim" "$R/rtl/dsrom_sys/s81_die_bind/test/tb_cfifo_return_launch.sv" "$R/rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_return_launch70.sv" "$R/rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_partitioned.sv" "$R/rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress.sv" "$R/rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv"
vvp "$OUT/sim"
