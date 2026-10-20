#!/bin/bash
# L2H-PAD l21 2026-10-19: Verilator 5.050 bench of the host observation readback ring
# (ot_hbm_host_static_ingress_obs + 3 ot_hbm_obs_leaf + relay stations).
#   obs_ring_bench.sh LMUT   (run from the source root; 0 = production must PASS; 1/2/3 = leaf mutants must FAIL)
set -o pipefail
M=${1:-0}; V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
SRCS="rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_obs_leaf.sv
rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress_obs.sv
rtl/hbm_accel/die_glue/tb/tb_hbm_obs_ring.sv"
$V --version
O=obj_obs_m$M; rm -rf $O
$V --binary -j 8 -Wno-fatal -Wno-lint -Wno-style --timing --top-module tb_hbm_obs_ring +define+LMUT=$M -Mdir $O $SRCS > $O.build.log 2>&1 || { tail -30 $O.build.log; echo BUILD_FAIL; exit 2; }
./$O/Vtb_hbm_obs_ring | tee $O.run.log
grep -q "OBS RING BENCH PASS" $O.run.log
