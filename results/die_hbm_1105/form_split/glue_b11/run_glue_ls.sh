#!/usr/bin/env bash
# HBM-FORM-SPLIT-8+REFORM-B11 glue lock-step: run_glue_ls.sh REF_RTL_DIR OUT [EPS] [CYC]
#   REF_RTL_DIR = the uncut kit rtl/ (hfd_hgi_vms_glue_tiles.sv, hfd_hgi_vms_static_glue.sv, ot_vms_*_static.sv)
#   MUT 0 must PASS, DMUT 1..4 must FAIL.
set -u
KR=$1; O=$2; EPS=${3:-40}; CYC=${4:-400}; H=$(cd "$(dirname "$0")" && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p "$O"
P=${PIECES:-$H/../../../../rtl/hbm_accel/cores_split/reform_1105s/glue}
REF="$KR/hfd_hgi_vms_glue_tiles.sv $KR/hfd_hgi_vms_static_glue.sv $KR/ot_vms_rstop_static.sv $KR/ot_vms_hub_static.sv $KR/ot_vms_rcl_static.sv $KR/ot_vms_status_static.sv"
for M in ${MUTS:-0 1 2 3 4}; do (
  rm -rf $O/obj_m$M
  prlimit --as=40000000000 $V --binary -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DDMUT=$M -DEPS=$EPS -DCYC=$CYC --top-module tb \
    -Mdir $O/obj_m$M -o sim $H/tb_glue.sv $REF $P/ot_vms_glue_pc.sv $P/hfd_hgi_vms_glue_nw_pieces.sv $H/hfd_hgi_vms_glue_nw_t__p11comp.sv > $O/build_m$M.log 2>&1 || { echo "MUT $M BUILD FAIL"; tail -5 $O/build_m$M.log; exit 2; }
  $O/obj_m$M/sim +verilator+seed+$((11+M)) > $O/sim_m$M.log 2>&1; echo "MUT $M: $(grep GLUE_LOCKSTEP $O/sim_m$M.log) $(tail -1 $O/sim_m$M.log)"
) & done; wait
sha256sum $REF $P/ot_vms_glue_pc.sv $P/hfd_hgi_vms_glue_nw_pieces.sv $H/hfd_hgi_vms_glue_nw_t__p11comp.sv $H/tb_glue.sv > $O/sources.sha256
