read_db /probe/work/orfs/results/asap7/opentallas_ot_v41_static_provider_context_asap7_epicurus_static_context_r1/base/2_3_floorplan_tapcell.odb
set b [ord::get_db_block]
foreach n [$b getNets] {if {[regexp {ph_q|st_q|phase_pair|stream_word|provider_addr|phase_launch} [$n getName]]} {puts [$n getName]}}
exit
