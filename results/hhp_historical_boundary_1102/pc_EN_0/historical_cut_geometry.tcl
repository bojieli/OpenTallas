# PRIVATE HISTORICAL ONLY: native M1 Y-pin shapes + canonical M9 strap subsets. NO via/route credit.
set dc_b [ord::get_db_block]
set dc_u [$dc_b getDbUnitsPerMicron]
set dc_tech [ord::get_db_tech]
set dc_t [$dc_b findBTerm {ckm_w_ckm_n10_h1111111101}]
if {$dc_t eq "NULL" || $dc_t eq ""} {error "HHP_CUT missing ckm_w_ckm_n10_h1111111101"}
set dc_n [$dc_t getNet]
if {$dc_n eq "NULL" || $dc_n eq ""} {error "HHP_CUT disconnected ckm_w_ckm_n10_h1111111101"}
$dc_n setSigType CLOCK
$dc_t setSigType CLOCK
foreach dc_p [$dc_t getBPins] {odb::dbBPin_destroy $dc_p}
set dc_p [odb::dbBPin_create $dc_t]
$dc_p setPlacementStatus FIXED
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(189.837000000*$dc_u)}] [expr {round(518.198000000*$dc_u)}] [expr {round(189.855000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(189.837000000*$dc_u)}] [expr {round(516.924000000*$dc_u)}] [expr {round(190.053000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(190.035000000*$dc_u)}] [expr {round(518.198000000*$dc_u)}] [expr {round(190.053000000*$dc_u)}]
set dc_t [$dc_b findBTerm {ckm_w_ckm_n10_h1111111100}]
if {$dc_t eq "NULL" || $dc_t eq ""} {error "HHP_CUT missing ckm_w_ckm_n10_h1111111100"}
set dc_n [$dc_t getNet]
if {$dc_n eq "NULL" || $dc_n eq ""} {error "HHP_CUT disconnected ckm_w_ckm_n10_h1111111100"}
$dc_n setSigType CLOCK
$dc_t setSigType CLOCK
foreach dc_p [$dc_t getBPins] {odb::dbBPin_destroy $dc_p}
set dc_p [odb::dbBPin_create $dc_t]
$dc_p setPlacementStatus FIXED
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(569.997000000*$dc_u)}] [expr {round(518.198000000*$dc_u)}] [expr {round(570.015000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(569.997000000*$dc_u)}] [expr {round(516.924000000*$dc_u)}] [expr {round(570.213000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(570.195000000*$dc_u)}] [expr {round(518.198000000*$dc_u)}] [expr {round(570.213000000*$dc_u)}]
set dc_t [$dc_b findBTerm {ckm_w_ckm_n10_h1111111001}]
if {$dc_t eq "NULL" || $dc_t eq ""} {error "HHP_CUT missing ckm_w_ckm_n10_h1111111001"}
set dc_n [$dc_t getNet]
if {$dc_n eq "NULL" || $dc_n eq ""} {error "HHP_CUT disconnected ckm_w_ckm_n10_h1111111001"}
$dc_n setSigType CLOCK
$dc_t setSigType CLOCK
foreach dc_p [$dc_t getBPins] {odb::dbBPin_destroy $dc_p}
set dc_p [odb::dbBPin_create $dc_t]
$dc_p setPlacementStatus FIXED
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(950.157000000*$dc_u)}] [expr {round(518.198000000*$dc_u)}] [expr {round(950.175000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(950.157000000*$dc_u)}] [expr {round(516.924000000*$dc_u)}] [expr {round(950.373000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(950.355000000*$dc_u)}] [expr {round(518.198000000*$dc_u)}] [expr {round(950.373000000*$dc_u)}]
set dc_t [$dc_b findBTerm {ckm_w_ckm_n10_h1111111000}]
if {$dc_t eq "NULL" || $dc_t eq ""} {error "HHP_CUT missing ckm_w_ckm_n10_h1111111000"}
set dc_n [$dc_t getNet]
if {$dc_n eq "NULL" || $dc_n eq ""} {error "HHP_CUT disconnected ckm_w_ckm_n10_h1111111000"}
$dc_n setSigType CLOCK
$dc_t setSigType CLOCK
foreach dc_p [$dc_t getBPins] {odb::dbBPin_destroy $dc_p}
set dc_p [odb::dbBPin_create $dc_t]
$dc_p setPlacementStatus FIXED
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(1330.317000000*$dc_u)}] [expr {round(518.198000000*$dc_u)}] [expr {round(1330.335000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(1330.317000000*$dc_u)}] [expr {round(516.924000000*$dc_u)}] [expr {round(1330.533000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M1}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(516.906000000*$dc_u)}] [expr {round(1330.515000000*$dc_u)}] [expr {round(518.198000000*$dc_u)}] [expr {round(1330.533000000*$dc_u)}]
set dc_t [$dc_b findBTerm {ck_mesh}]
if {$dc_t eq "NULL" || $dc_t eq ""} {error "HHP_CUT missing ck_mesh"}
set dc_n [$dc_t getNet]
if {$dc_n eq "NULL" || $dc_n eq ""} {error "HHP_CUT disconnected ck_mesh"}
$dc_n setSigType CLOCK
$dc_t setSigType CLOCK
foreach dc_p [$dc_t getBPins] {odb::dbBPin_destroy $dc_p}
set dc_p [odb::dbBPin_create $dc_t]
$dc_p setPlacementStatus FIXED
set dc_l [$dc_tech findLayer {M9}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(357.800000000*$dc_u)}] [expr {round(285.015000000*$dc_u)}] [expr {round(357.960000000*$dc_u)}] [expr {round(285.495000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M9}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(357.800000000*$dc_u)}] [expr {round(475.095000000*$dc_u)}] [expr {round(357.960000000*$dc_u)}] [expr {round(475.575000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M9}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(677.480000000*$dc_u)}] [expr {round(285.015000000*$dc_u)}] [expr {round(677.640000000*$dc_u)}] [expr {round(285.495000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M9}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(677.480000000*$dc_u)}] [expr {round(474.825000000*$dc_u)}] [expr {round(677.640000000*$dc_u)}] [expr {round(475.305000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M9}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(677.480000000*$dc_u)}] [expr {round(1045.335000000*$dc_u)}] [expr {round(677.640000000*$dc_u)}] [expr {round(1045.815000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M9}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(677.480000000*$dc_u)}] [expr {round(1235.145000000*$dc_u)}] [expr {round(677.640000000*$dc_u)}] [expr {round(1235.625000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M9}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(357.800000000*$dc_u)}] [expr {round(1045.335000000*$dc_u)}] [expr {round(357.960000000*$dc_u)}] [expr {round(1045.815000000*$dc_u)}]
set dc_l [$dc_tech findLayer {M9}]
if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}
odb::dbBox_create $dc_p $dc_l [expr {round(357.800000000*$dc_u)}] [expr {round(1235.145000000*$dc_u)}] [expr {round(357.960000000*$dc_u)}] [expr {round(1235.625000000*$dc_u)}]
