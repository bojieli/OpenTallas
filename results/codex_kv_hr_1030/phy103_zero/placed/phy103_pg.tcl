read_db /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/3_place.odb
source /work/pg_connect.tcl
ot_pg_connect_all phy103_place
ot_pg_require_bound phy103_place
write_db /work/3_place_pg_bound.odb
puts PHY103_PLACE_PG_BOUND_DONE_NO_CTS_GRT_STA
