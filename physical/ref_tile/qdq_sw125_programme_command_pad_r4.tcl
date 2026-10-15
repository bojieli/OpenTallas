# Targeted actual-native correction, after recipe2 pads and before pin-flop anchoring.
# Baseline 4d4ac803c routed FF hold for command1..17 >=60.574ps; actual HB2 trio
# FF delay <=~45.5ps on measured paths. Remove only these17trios, preserving all
# other output/input hold pads. New route/FF/native proof mandatory, no waiver.
set qdq_blk [ord::get_db_block]
set qdq_count 0
foreach qdq_bt [$qdq_blk getBTerms] {
    set qdq_name [regsub -all {\\} [$qdq_bt getName] {}]
    if {![regexp {^command\[([0-9]+)\]$} $qdq_name -> qdq_bit]} continue
    if {$qdq_bit<1 || $qdq_bit>17} continue
    set qdq_net [$qdq_bt getNet]
    set qdq_tail ""
    foreach qdq_it [$qdq_net getITerms] {
        if {[$qdq_it isOutputSignal]} {set qdq_tail [$qdq_it getInst];break}
    }
    if {$qdq_tail eq "" || ![regexp {^ot_ohdrv_([0-9]+)_2$} [$qdq_tail getName] -> qdq_id]} {
        error "QDQ_R4 expected exact existing padtrio at $qdq_name"
    }
    set qdq_mid [$qdq_blk findInst ot_outhold_${qdq_id}_1]
    set qdq_lead [$qdq_blk findInst ot_ohdrv_${qdq_id}_0]
    if {$qdq_mid eq "NULL" || $qdq_lead eq "NULL"} {error "QDQ_R4 missing padchain $qdq_name"}
    set qdq_source [[$qdq_lead findITerm A] getNet]
    set qdq_dead [list $qdq_net [[$qdq_tail findITerm A] getNet] [[$qdq_mid findITerm A] getNet]]
    $qdq_bt disconnect
    $qdq_bt connect $qdq_source
    foreach qdq_i [list $qdq_tail $qdq_mid $qdq_lead] {
        catch {unset_dont_touch [get_cells [$qdq_i getName]]}
        $qdq_i setDoNotTouch 0
        odb::dbInst_destroy $qdq_i
    }
    foreach qdq_n $qdq_dead {
        $qdq_n setDoNotTouch 0
        if {[llength [$qdq_n getITerms]] || [llength [$qdq_n getBTerms]]} {error "QDQ_R4 padnet still used $qdq_name"}
        odb::dbNet_destroy $qdq_n
    }
    incr qdq_count
}
if {$qdq_count!=17} {error "QDQ_R4 pruned $qdq_count expected17"}
puts "QDQ_R4 removed17measuredcommandpadtrios; functionalregisteredgesunchanged"
