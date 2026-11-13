#!/bin/bash
# Generate the v8 g0 / g1 kits through the recipe path (run from a checkout of this branch; REPO = this tree).
# PLAN = a copy of plan_t39w whose cores/ot_wbq_root_g1__216x129.6__vC5.json and cores/ot_wbq_root_g__216x129.6__d44v_p51.json are the
# tables/*__clk52.json files and whose clock_entries.json carries tables/wbq_root_clkpins_1112_delta.json clock_entries_edits;
# VIEWS = core_views json of that plan with the two pins_sha256 updated. MACRO = json with macro_placement k=0..3 (ot_sram_1r1w_128x256_m1_r0c0_g256,
# origin x 100.032, y 14.892 / 42.492 / 70.092 / 97.692, orient MY).
set -e
VIEWS=$1; MACRO=$2; OUT=$3
for p in "ot_wbq_root_g0@73293b760213 g0" "ot_wbq_root_g1@d30c289f282d g1"; do set -- $p
  python3 physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py --views $VIEWS --view $1 --out $OUT/$2 --clock-pin-entry on --core-macros off \
    --macro-placement $MACRO --macro-inst-fmt 'u_grp.g_lane[{k}].u_payload' --face-reset-relay 2 --sigmax M6 --util 0.40 --slew-margin 20 \
    --clock-taps density --max-wire-um 100 --orfs-var OT_HOLD_REPAIR_SCOPE=reg2reg --orfs-var OT_FF_CHAIN_PIN=1 --orfs-var OT_RST_COPIES_MAX=64
done
# Then (as built): copy ot_rst_copies.tcl/.py and the clock_pin_landing_guard.tcl + core_drt_post.tcl of the CORE-WBQ-1 staging into the kit,
# add the OT_CPL add block to core_grt_pre.tcl and `export POST_DETAIL_ROUTE_TCL = /work/core_drt_post.tcl` to config.mk,
# then run_kit_hbm.sh KIT route 64 16 and eco_loop.py run --kit KIT --runner KIT/run_kit_hbm.sh --out KIT/eco_1 --mem 64 --cpus 16.
