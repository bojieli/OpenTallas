# Read-only actual reset-cone clock measurement, no binding or physical gate.
sta::find_timing_paths -path_delay max -group_path_count 1
set fp [open /work/reset_clock_probe.tsv w]
foreach name {
{rly_rst_d2d__fo1_0/ck}
{rly_rst_d2d__fo1_1/ckf}
{rly_rst_d2d__fo1_2/ck}
{rs_bump/ck}
{rstseq_rom/ck}
{rstt_rst_d2d__fo1__r3_0/clk}
{rstt_rst_d2d__fo1__r3_19/clk}
{rstt_rst_d2d__fo1__r3_20/clk}
{rstt_rst_d2d__fo1__r3_21/clk}
{rstt_rst_d2d__fo1__r3_24/clk}
{rstt_rst_d2d__fo1__r3_28/clk}
{rstt_rst_d2d__fo1__r3_31/clk}
{rstt_rst_d2d__fo1__r3_34/clk}
{rstt_rst_fwd_s_0/clk}
{rstt_rst_fwd_s_1/clk}
{rstt_rst_fwd_s_10/clk}
{rstt_rst_fwd_s_12/clk}
{rstt_rst_fwd_s_13/clk}
{rstt_rst_fwd_s_14/clk}
{rstt_rst_fwd_s_16/clk}
{rstt_rst_fwd_s_4/clk}
{rstt_rst_fwd_s_5/clk}
{rstt_rst_fwd_s_6/clk}
{rstt_rst_fwd_s_8/clk}
{rstt_rst_fwd_s_9/clk}
{rstt_rst_seq_0/clk}
{rstt_rst_seq_20/clk}
{rstt_rst_seq_21/clk}
{rstt_rst_seq_22/clk}
{rstt_rst_seq_24/clk}
{rstt_rst_seq_30/clk}
{rstt_rst_seq_33/clk}
{rstt_rst_seq_36/clk}
{rstt_rst_seq_40/clk}
{rstt_rst_seq_42/clk}
{rstt_rst_seq_44/clk}
{rstt_rst_seq_46/clk}
{rstt_rst_seq_48/clk}
{rstt_rst_seq_66/clk}
{rly_lnk_native_tx_slot_0/ck_s}
{rly_lnk_native_tx_slot_0/ck}
} {
  set pins [get_pins -quiet $name]
  if {[llength $pins] == 0} {set pins [get_pins -quiet "${name}\[0\]"]}
  if {[llength $pins] != 1} {puts $fp "$name\tMISSING_OR_AMBIGUOUS"; continue}
  set pin [lindex $pins 0]
  if {[catch {set late [get_property $pin arrival_max_rise]; set early [get_property $pin arrival_min_rise]} why]} {puts $fp "$name\tPROPERTY_ERROR\t$why"; continue}
  puts $fp "$name\t[get_full_name $pin]\t$late\t$early"
}
close $fp
puts OT_RESET_CONE_PROBE_DONE
exit
