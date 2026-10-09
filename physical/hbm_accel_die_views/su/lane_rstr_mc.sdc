# struct-close 2026-10-09: ot_su12_lane RSTR=1: the registered lane reset (rst_q) is held for >= 8 edges around every
# reset, so its fan-out tree into the lane's synchronous reset logic is a 4-cycle path (setup 4 / hold 3).  Only the
# rst_q flop's fan-out: every datapath stays single-cycle.
set ot_rq [get_cells -hierarchical -quiet *rst_q*]
if {[llength $ot_rq] == 0} { error "lane_rstr_mc: rst_q not found (RSTR=1 build expected)" }
set_multicycle_path -setup 4 -from $ot_rq
set_multicycle_path -hold 3 -from $ot_rq
puts "lane_rstr_mc: [llength $ot_rq] rst_q cell(s): 4-cycle reset tree"
