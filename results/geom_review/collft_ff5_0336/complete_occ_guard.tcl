# Exact pre-anchor allocator occupancy, including software-reserved status footprints.
set nf_occ_f [open /work/pre_anchor_occupancy.tsv r]
gets $nf_occ_f nf_occ_header
if {$nf_occ_header ne "row\tlo\thi"} {error "NF invalid expected occupancy header"}
set nf_occ_expected {}
while {[gets $nf_occ_f nf_occ_line]>=0} {
 lassign [split $nf_occ_line "\t"] nf_occ_r nf_occ_lo nf_occ_hi
 if {![string is integer -strict $nf_occ_r] || ![string is integer -strict $nf_occ_lo] || ![string is integer -strict $nf_occ_hi] || $nf_occ_lo>$nf_occ_hi} {error "NF invalid expected occupancy interval"}
 dict lappend nf_occ_expected $nf_occ_r [list $nf_occ_lo $nf_occ_hi]
}
close $nf_occ_f
if {[lsort -integer [dict keys $nf_occ_expected]] ne [lsort -integer [dict keys $::cland_occ]]} {error "NF complete pre-anchor occupied row set changed"}
dict for {nf_occ_r nf_occ_intervals} $nf_occ_expected {
 if {[lsort -integer -index 0 $nf_occ_intervals] ne [lsort -integer -index 0 [dict get $::cland_occ $nf_occ_r]]} {error "NF complete pre-anchor occupancy changed at row $nf_occ_r"}
}
puts "NF COMPLETE PRE-ANCHOR OCCUPANCY MATCH [dict size $nf_occ_expected] rows"
unset nf_occ_expected nf_occ_header nf_occ_line nf_occ_f nf_occ_r nf_occ_lo nf_occ_hi nf_occ_intervals
