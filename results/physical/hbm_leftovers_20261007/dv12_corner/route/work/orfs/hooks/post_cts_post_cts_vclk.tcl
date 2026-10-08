# POST_CTS: vclk re-set to the measured insertion after the CTS-stage repair (or first set, when it was skipped)
source /src/physical/hbm_accel_die_views/common/vclk_latency.tcl
ot_vclk_from_insertion 1
