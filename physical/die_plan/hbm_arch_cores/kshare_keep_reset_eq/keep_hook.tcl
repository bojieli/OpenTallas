# the OT_KEEP_WIRES=reset_pipe part of the kit ot_keep_regs.tcl (same selections, same order)
yosys select -set ot_kwn w:reset_pipe w:reset_pipe\[\[\]* w:*.reset_pipe w:*.reset_pipe\[\[\]*
yosys setattr -set keep 1 @ot_kwn
yosys proc
yosys select -set ot_kw w:* a:keep %i
yosys select -set ot_kc @ot_kw %ci1 t:\$*dff* t:\$*dlatch* %u %i
yosys techmap @ot_kc
yosys select -set ot_kc @ot_kw %ci1 t:\$*dff* t:\$*dlatch* t:\$_*DFF* t:\$_*LATCH* %u %u %u %i
yosys setattr -set keep 1 @ot_kc
puts "OT_KEEP_REGS: [llength [split [string trim [yosys tee -q -s result.string select -list @ot_kc]] "\n"]] keep cells"
yosys select -clear
