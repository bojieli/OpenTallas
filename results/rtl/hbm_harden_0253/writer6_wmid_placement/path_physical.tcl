set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/4_1_cts.odb
set wanted {{_38214_} {_38216_} {_38225_} {_38242_} {_38243_} {clkbuf_0_clk_body} {clkbuf_0_clk_meta} {clkbuf_1_1_0_clk_body} {clkbuf_1_1_1_clk_body} {clkbuf_2_0_0_clk_meta} {clkbuf_3_7_0_clk_body} {clkbuf_3_7_1_clk_body} {clkbuf_4_15__f_clk_body} {clkbuf_leaf_99_clk_body} {core.sid_q[0]$_DFF_P_} {ot_prs_00000_ff} {place13116} {place13117} {place13118} {place13119} {place13126} {place14486} {place14487} {place14488} {place14489}}
set f [open /out/worst_path_physical.tsv w]
puts $f "instance	master	x_dbu	y_dbu	pins_and_nets"
foreach inst [[ord::get_db_block] getInsts] {
 set key [string map [list [format %c 92] ""] [$inst getName]]
 if {$key ni $wanted} continue
 lassign [$inst getLocation] x y
 set pairs {}
 foreach it [$inst getITerms] {set net [$it getNet];if {$net ne "NULL"} {lappend pairs "[[$it getMTerm] getName]=[$net getName]"}}
 puts $f "$key	[[$inst getMaster] getName]	$x	$y	[join $pairs {;}]"
}
close $f
puts "WORST_PATH_PHYSICAL_DONE"
exit
