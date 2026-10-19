set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set by {}
foreach i [$b getInsts] {dict set by [string map {\\ {}} [$i getName]] $i}
set seen 0
set name {g_pc[0].u_pc.u_q.g_bank[0].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(43.2*$dbu)}] [expr {round(172.8*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[0].u_pc.u_q.g_bank[1].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(129.6*$dbu)}] [expr {round(172.8*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[0].u_pc.u_q.g_bank[2].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(216.0*$dbu)}] [expr {round(172.8*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[0].u_pc.u_q.g_bank[3].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(43.2*$dbu)}] [expr {round(216.0*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[0].u_pc.u_q.g_bank[4].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(129.6*$dbu)}] [expr {round(216.0*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[0].u_pc.u_q.g_bank[5].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(216.0*$dbu)}] [expr {round(216.0*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[0].u_pc.u_r.g_bank[0].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(43.2*$dbu)}] [expr {round(43.2*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[0].u_pc.u_r.g_bank[1].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(129.6*$dbu)}] [expr {round(43.2*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[0].u_pc.u_r.g_bank[2].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(216.0*$dbu)}] [expr {round(43.2*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[0].u_pc.u_r.g_bank[3].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(43.2*$dbu)}] [expr {round(86.4*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[0].u_pc.u_r.g_bank[4].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(129.6*$dbu)}] [expr {round(86.4*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_q.g_bank[0].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(302.4*$dbu)}] [expr {round(172.8*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_q.g_bank[1].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(388.79999999999995*$dbu)}] [expr {round(172.8*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_q.g_bank[2].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(475.2*$dbu)}] [expr {round(172.8*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_q.g_bank[3].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(302.4*$dbu)}] [expr {round(216.0*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_q.g_bank[4].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(388.79999999999995*$dbu)}] [expr {round(216.0*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_q.g_bank[5].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(475.2*$dbu)}] [expr {round(216.0*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_r.g_bank[0].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(302.4*$dbu)}] [expr {round(43.2*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_r.g_bank[1].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(388.79999999999995*$dbu)}] [expr {round(43.2*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_r.g_bank[2].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(475.2*$dbu)}] [expr {round(43.2*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_r.g_bank[3].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(302.4*$dbu)}] [expr {round(86.4*$dbu)}]; $found setPlacementStatus FIRM
incr seen
set name {g_pc[1].u_pc.u_r.g_bank[4].u_mem}
set found {}
dict for {n i} $by {if {$n eq $name || $n eq "u_ot_pr_core.$name" || $n eq "u_ot_pr_core/$name"} {set found $i}}
if {$found eq {}} {error "missing actual bank $name"}
$found setOrient R0; $found setLocation [expr {round(388.79999999999995*$dbu)}] [expr {round(86.4*$dbu)}]; $found setPlacementStatus FIRM
incr seen
puts "BANK64_PLACED_MODEL macros=$seen"
if {$seen != 22} {error "expected22 actual banks"}
