# Useful skew for the ROM read (S6): the macro's SS clk->q (752-755 ps) + capture setup (22 ps) + 60 ps uncertainty
# exceed the 833 ps period unless the ROM clock leads its capture flops.  TritonCTS balances the macro clock net to the
# register tree with a chain of delay buffers (delaybuf_<k>_<clk>); removing the last QSS_ROM_LEAD_BUFS of them
# (~34 ps each at SS) makes every ROM clock pin lead by that much.  The cost is on the request side (R3 -> macro
# ce_in/addr_in setup, 146 / 399 ps slack in r3d) and nothing is relaxed: every path is still timed.
proc qss_rom_lead {n} {
  if {$n <= 0} { return }
  set block [ord::get_db_block]
  set bufs {}
  foreach inst [$block getInsts] {
    if {[regexp {^delaybuf_([0-9]+)_clk$} [$inst getName] -> k]} { lappend bufs [list $k $inst] }
  }
  set bufs [lsort -integer -decreasing -index 0 $bufs]
  if {[llength $bufs] < $n} { error "QSS rom_lead: only [llength $bufs] delay buffers, asked $n" }
  foreach kb [lrange $bufs 0 [expr {$n - 1}]] {
    set inst [lindex $kb 1]
    set in_net [[$inst findITerm A] getNet]
    set out_net [[$inst findITerm Y] getNet]
    foreach it [$out_net getITerms] {
      if {[$it getInst] ne $inst} { $it disconnect; $it connect $in_net }
    }
    puts "QSS rom_lead: removed [$inst getName] ([$out_net getName] -> [$in_net getName])"
    odb::dbInst_destroy $inst
    odb::dbNet_destroy $out_net
  }
}
