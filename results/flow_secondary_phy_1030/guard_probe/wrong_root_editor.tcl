# Deliberate wrong-root mutant, in-memory diagnostic only.
set b [ord::get_db_block]; set phy [[$b findBTerm {clk_clk_phy[0]}] getNet]
set target [[$b findBTerm clk] getNet]
set pin {}
foreach it [$phy getITerms] {if {[[$it getMTerm] getName] eq "CLK" && ![[[$it getInst] getMaster] isBlock]} {set pin $it;break}}
if {$pin eq {}} {error MUTANT_NO_FF}
set inst [$pin getInst];set dt [$inst isDoNotTouch];$inst setDoNotTouch 0
try {$pin disconnect; $pin connect $target} finally {$inst setDoNotTouch $dt}
puts "MUTANT_REWIRED [[$pin getInst] getName]/[[$pin getMTerm] getName] to [$target getName]"
