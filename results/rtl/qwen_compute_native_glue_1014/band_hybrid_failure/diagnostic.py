from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/ref_gate/qfd_sp_band_lanes_native-20261014-204626')
lines=(r/'cts.log').read_text().splitlines();i=lines.index('Running cts.tcl, stage 4_1_cts')
sel=[x for x in lines[i:] if x.startswith(('read_liberty ','read_db ','read_sdc '))]
t='define_corners WC BC\n'+'\n'.join(sel)+'\n'
t+='''set block [ord::get_db_block]

set src [get_ports ck]
set ep [get_fanout -flat -endpoints_only -from $src]
set regs [all_registers -clock ot_entry_0 -clock_pins]
set rn {};foreach p $regs {lappend rn [get_full_name $p]}
puts "COUNT ep=[llength $ep] regs=[llength $regs]"
set bad 0
foreach p $ep {
set cell [get_cells -quiet -of_objects $p]
set inst [$block findInst [get_full_name $cell]]
if {$inst eq "NULL"} {puts "NULLINST [get_full_name $p] cell=[get_full_name $cell]"; incr bad} elseif {[[$inst getMaster] isBlock] || [get_full_name $p] ni $rn} {puts "BAD [get_full_name $p] cell=[get_full_name $cell] block=[[$inst getMaster] isBlock]"; incr bad};if {$bad > 20} {break}
}
'''
(r/'diagnostic.tcl').write_text(t)
