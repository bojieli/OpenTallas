# GX7 / SC-19 (hgi-takeover 2026-10-09): ot_hgi_mtp_core18 RSTR=1.  The core's synchronised reset flop u_core.rst_s[1]
# fans out to every async reset pin of the core; its release is a 4-cycle path (setup 4 / hold 3, hold stays at the
# launch edge).  Only that flop's fan-out; every datapath stays single-cycle.  Validity: no input is used within 4
# cycles of release (bench HELD_RELEASE_CHECK; die config settle >> 4 cycles).
set ot_rs [get_cells -hierarchical -quiet {*u_core*rst_s?1??_DFF*}]
if {[llength $ot_rs] == 0} { error "mtp18_rstr_mc: rst_s[1] not found" }
set_multicycle_path -setup 4 -from $ot_rs
set_multicycle_path -hold 3 -from $ot_rs
puts "mtp18_rstr_mc: [llength $ot_rs] rst_s[1] cell(s): 4-cycle reset tree"
