#!/bin/bash
set -eu
cd "$(dirname "$0")/../../../../.."
out=$(realpath -m "$1"); mkdir -p "$out"
defs=(); if [ "${2:-base}" = mutant ]; then defs=(-DOT_HBM_COLL_FACE_EARLY); fi
iverilog -g2012 "${defs[@]}" -s tb_hbm_coll_face_pipe512 -o "$out/sim" rtl/hbm_accel/generic/collective/physical/tb_hbm_coll_face_pipe512.sv rtl/hbm_accel/generic/collective/physical/ot_hbm_coll_face_pipe512.sv physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv
vvp "$out/sim"
