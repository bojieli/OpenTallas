#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TASK_OUT=${1:?output directory}; TASK_MUT=${2:-0}
mkdir -p "$TASK_OUT"
TASK_DEFS=(-DDSFD_PQ_STATIC_X2)
case "$TASK_MUT" in 0) ;; 1) TASK_DEFS+=(-DDSFD_PQ_X2_MUT_SWAP);; 2) TASK_DEFS+=(-DDSFD_PQ_LX_MUT_SWAP);; *) exit 2;; esac
iverilog -g2012 "${TASK_DEFS[@]}" -s tb_s81_pq_static_x2 -o "$TASK_OUT/sim" "$TASK_ROOT/rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv" "$TASK_ROOT/rtl/test/dsrom_sys/tb_s81_pq_static_x2.sv"
vvp "$TASK_OUT/sim"
