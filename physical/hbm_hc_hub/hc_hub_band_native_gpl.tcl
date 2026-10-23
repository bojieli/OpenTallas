# HBM-COLLECT10/HCQB 10-21 (hub cluster kits hbm_hcq_hub_c1p / c1q): PRE_GLOBAL_PLACE.  ORFS takes one hook per step, so
# the two repo hooks the hub cluster needs are sourced here:
#  1. native_untouch.tcl -- the LAT-7 native-fanout adder graph (rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v) carries
#     (* keep, dont_touch *) on all 3,500 cells; hbm_hcq_hub_c1p-c1p-9a9e8c85b crashed twice in 3_3_place_gp at the
#     first timing-driven repair: ODB-1211 load pin ...g_lvl[6].g_n[0].u_a.genblk1.g_native7.u_native.c904/B1 is
#     dont_touch -> RSZ-3006 (net n1957 = OAI311xp33 driving 24 OAI loads).  The tree16 child kits already clear the
#     physical dont_touch (pre_gpl.tcl); the hub kit's band hook did not.
#  2. hc_hub_band_gpl.tcl -- the central standard-cell band (GPL-only region, removed again before DPL).
source /src/physical/hbm_hc_hub/native_untouch.tcl
source /src/physical/hbm_hc_hub/hc_hub_band_gpl.tcl
