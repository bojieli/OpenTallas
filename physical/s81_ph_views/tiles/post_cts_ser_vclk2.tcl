# CLAUDE S81-PH capture tiles POST_CTS: the ckv-root balance (pre_cts_ser_balance.tcl; a no-op when the CTS-stage
# repair already ran it), then vclk / vclk_s at the measured insertions (common/post_cts_vclk2.tcl).
source /src/physical/s81_ph_views/tiles/pre_cts_ser_balance.tcl
ot_ser_balance
detailed_placement
source /src/physical/s81_ph_views/common/post_cts_vclk2.tcl
