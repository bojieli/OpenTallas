set b [lindex [glob /work/results/asap7/*/base] 0]
read_db $b/3_3_place_gp.odb
set count 0;set wrong {}
foreach p [[ord::get_db_block] getBTerms] {
 if {[$p getIoType] ne "OUTPUT"} {continue}
 set drivers {}
 foreach t [[$p getNet] getITerms] {if {[$t getIoType] eq "OUTPUT"} {lappend drivers $t}}
 if {[llength $drivers]!=1} {error "expected one physical output driver"}
 set m [[[lindex $drivers 0] getInst] getMaster]
 puts "OUTPUT_DRIVER [$p getName] [$m getName]"
 if {[$m getName] ne "BUFx24_ASAP7_75t_R"} {lappend wrong [$p getName]}
 incr count
}
puts "OUTPUT_MASTER_COUNT $count WRONG_MASTER [llength $wrong]"
source /src/tools/fp_margin_lint.tcl
ot_fp_lint_dump /receipt/fp_dump.json
if {$count!=258 || [llength $wrong]} {error "strong outputs did not survive actual3_3"}
puts OT_MAPPED_OUTPUT_MASTER_PASS
