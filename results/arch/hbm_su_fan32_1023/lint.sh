#!/bin/bash
set -euo pipefail
$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --lint-only -Wno-fatal -Wno-MODMISSING -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD --top-module ot_hbm_su_static_pgslice_rgf_lp_n32 ot_hbm_su_static_pgslice_rgf_lp_n32.sv ot_hbm_su_pgrg_parts.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv ot_pl_land_split.sv ot_pl_land_rst_copy.sv > lint.log 2>&1
