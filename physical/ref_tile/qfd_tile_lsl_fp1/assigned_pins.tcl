# Exact inherited pin rectangles, die assignment23dca4512; legacy LEF SHA7da1730df88a3fcbedb7dc607af06dc80453f422fe8a13e4955619eab0ece8c4
set lsl_block [ord::get_db_block]
set lsl_tech [ord::get_db_tech]
set lsl_dbu [$lsl_block getDbUnitsPerMicron]
set lsl_bt [$lsl_block findBTerm {clk}]
if {$lsl_bt == "NULL"} {error "missing assigned pin clk"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(62.976*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(63.0*$lsl_dbu)}]
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.445*$lsl_dbu)}] [expr {round(62.976*$lsl_dbu)}] [expr {round(99.756*$lsl_dbu)}] [expr {round(63.0*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {first_d}]
if {$lsl_bt == "NULL"} {error "missing assigned pin first_d"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(64.992*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(65.016*$lsl_dbu)}]
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(98.557*$lsl_dbu)}] [expr {round(64.992*$lsl_dbu)}] [expr {round(99.756*$lsl_dbu)}] [expr {round(65.016*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {lfault[0]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin lfault[0]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(104.208*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(104.232*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {lfault[1]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin lfault[1]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(104.592*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(104.616*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {lfault[2]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin lfault[2]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(105.024*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(105.048*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {lfault[3]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin lfault[3]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(105.408*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(105.432*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {lfault[4]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin lfault[4]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(105.84*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(105.864*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {lfault[5]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin lfault[5]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(106.272*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(106.296*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {lfault[6]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin lfault[6]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(106.656*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(106.68*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {lfault[7]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin lfault[7]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(107.088*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(107.112*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {rst_n}]
if {$lsl_bt == "NULL"} {error "missing assigned pin rst_n"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(67.008*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(67.032*$lsl_dbu)}]
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.673*$lsl_dbu)}] [expr {round(67.008*$lsl_dbu)}] [expr {round(99.756*$lsl_dbu)}] [expr {round(67.032*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {split_d[0]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin split_d[0]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(68.976*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(69.0*$lsl_dbu)}]
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.349*$lsl_dbu)}] [expr {round(68.976*$lsl_dbu)}] [expr {round(99.756*$lsl_dbu)}] [expr {round(69.0*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {split_d[1]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin split_d[1]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(70.992*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(71.016*$lsl_dbu)}]
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.673*$lsl_dbu)}] [expr {round(70.992*$lsl_dbu)}] [expr {round(99.756*$lsl_dbu)}] [expr {round(71.016*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {split_d[2]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin split_d[2]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(73.008*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(73.032*$lsl_dbu)}]
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.493*$lsl_dbu)}] [expr {round(73.008*$lsl_dbu)}] [expr {round(99.756*$lsl_dbu)}] [expr {round(73.032*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {split_d[3]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin split_d[3]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(74.976*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(75.0*$lsl_dbu)}]
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.673*$lsl_dbu)}] [expr {round(74.976*$lsl_dbu)}] [expr {round(99.756*$lsl_dbu)}] [expr {round(75.0*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[0]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[0]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(107.472*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(107.496*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[10]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[10]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(111.6*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(111.624*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[11]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[11]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(111.984*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(112.008*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[12]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[12]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(112.416*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(112.44*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[13]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[13]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(112.848*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(112.872*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[14]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[14]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(113.232*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(113.256*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[15]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[15]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(113.664*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(113.688*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[16]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[16]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(114.048*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(114.072*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[17]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[17]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(114.48*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(114.504*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[18]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[18]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(114.864*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(114.888*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[19]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[19]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(115.296*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(115.32*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[1]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[1]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(107.904*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(107.928*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[20]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[20]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(115.68*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(115.704*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[21]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[21]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(116.112*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(116.136*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[22]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[22]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(116.544*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(116.568*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[23]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[23]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(116.928*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(116.952*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[24]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[24]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(117.312*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(117.344*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[25]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[25]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(117.76*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(117.792*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[26]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[26]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(118.144*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(118.176*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[27]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[27]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(118.592*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(118.624*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[28]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[28]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(118.976*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(119.008*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[29]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[29]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(119.424*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(119.456*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[2]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[2]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(108.288*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(108.312*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[30]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[30]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(119.808*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(119.84*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[31]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[31]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(120.192*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(120.224*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[32]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[32]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(120.64*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(120.672*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[33]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[33]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(121.024*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(121.056*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[34]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[34]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(121.472*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(121.504*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[35]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[35]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(121.856*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(121.888*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[36]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[36]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(122.304*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(122.336*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[37]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[37]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(122.688*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(122.72*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[38]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[38]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(123.072*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(123.104*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[39]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[39]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(123.52*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(123.552*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[3]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[3]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(108.72*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(108.744*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[40]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[40]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(123.904*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(123.936*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[41]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[41]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(124.352*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(124.384*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[42]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[42]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(124.736*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(124.768*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[43]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[43]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(125.12*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(125.152*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[44]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[44]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(125.568*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(125.6*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[45]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[45]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(125.952*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(125.984*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[46]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[46]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(126.4*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(126.432*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[47]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[47]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(126.784*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(126.816*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[48]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[48]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(127.232*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(127.264*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[49]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[49]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(127.616*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(127.648*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[4]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[4]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(109.104*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(109.128*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[50]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[50]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(128.0*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(128.032*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[51]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[51]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(128.448*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(128.48*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[52]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[52]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(128.832*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(128.864*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[53]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[53]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(129.28*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(129.312*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[54]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[54]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(129.664*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(129.696*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[55]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[55]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(130.112*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(130.144*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[56]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[56]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(130.512*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(130.536*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[57]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[57]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(130.896*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(130.92*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[58]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[58]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(131.328*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(131.352*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[59]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[59]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(131.712*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(131.736*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[5]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[5]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(109.536*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(109.56*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[60]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[60]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(132.144*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(132.168*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[61]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[61]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(132.528*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(132.552*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[62]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[62]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(132.96*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(132.984*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[63]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[63]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(133.392*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(133.416*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[6]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[6]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(109.968*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(109.992*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[7]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[7]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(110.352*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(110.376*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[8]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[8]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(110.784*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(110.808*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {t_out[9]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin t_out[9]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(111.168*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(111.192*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {tfault}]
if {$lsl_bt == "NULL"} {error "missing assigned pin tfault"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(133.776*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(133.8*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {v_d}]
if {$lsl_bt == "NULL"} {error "missing assigned pin v_d"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(76.992*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(77.016*$lsl_dbu)}]
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.493*$lsl_dbu)}] [expr {round(76.992*$lsl_dbu)}] [expr {round(99.756*$lsl_dbu)}] [expr {round(77.016*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[0]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[0]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(6.096*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(6.12*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[100]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[100]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(27.968*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(28.0*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[101]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[101]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(28.16*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(28.192*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[102]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[102]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(28.416*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(28.448*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[103]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[103]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(28.608*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(28.64*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[104]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[104]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(28.864*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(28.896*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[105]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[105]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(29.056*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(29.088*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[106]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[106]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(29.312*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(29.344*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[107]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[107]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(29.504*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(29.536*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[108]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[108]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(29.696*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(29.728*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[109]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[109]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(29.952*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(29.984*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[10]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[10]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(8.304*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(8.328*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[110]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[110]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(30.144*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(30.176*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[111]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[111]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(30.4*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(30.432*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[112]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[112]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(30.592*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(30.624*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[113]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[113]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(30.784*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(30.816*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[114]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[114]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(31.04*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(31.072*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[115]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[115]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(31.232*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(31.264*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[116]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[116]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(31.488*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(31.52*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[117]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[117]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(31.68*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(31.712*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[118]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[118]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(31.936*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(31.968*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[119]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[119]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(32.128*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(32.16*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[11]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[11]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(8.496*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(8.52*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[120]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[120]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(32.32*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(32.352*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[121]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[121]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(32.576*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(32.608*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[122]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[122]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(32.768*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(32.8*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[123]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[123]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(33.024*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(33.056*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[124]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[124]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(33.216*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(33.248*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[125]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[125]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(33.408*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(33.44*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[126]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[126]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(33.664*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(33.696*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[127]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[127]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(33.856*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(33.888*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[128]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[128]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(34.08*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(34.104*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[129]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[129]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(34.32*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(34.344*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[12]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[12]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(8.736*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(8.76*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[130]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[130]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(34.512*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(34.536*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[131]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[131]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(34.752*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(34.776*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[132]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[132]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(34.992*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(35.016*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[133]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[133]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(35.184*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(35.208*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[134]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[134]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(35.424*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(35.448*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[135]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[135]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(35.616*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(35.64*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[136]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[136]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(35.856*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(35.88*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[137]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[137]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(36.048*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(36.072*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[138]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[138]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(36.288*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(36.312*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[139]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[139]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(36.528*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(36.552*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[13]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[13]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(8.928*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(8.952*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[140]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[140]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(36.72*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(36.744*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[141]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[141]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(36.96*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(36.984*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[142]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[142]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(37.152*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(37.176*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[143]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[143]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(37.392*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(37.416*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[144]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[144]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(37.584*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(37.608*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[145]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[145]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(37.824*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(37.848*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[146]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[146]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(38.016*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(38.04*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[147]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[147]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(38.256*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(38.28*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[148]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[148]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(38.496*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(38.52*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[149]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[149]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(38.688*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(38.712*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[14]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[14]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(9.168*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(9.192*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[150]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[150]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(38.928*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(38.952*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[151]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[151]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(39.12*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(39.144*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[152]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[152]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(39.36*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(39.384*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[153]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[153]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(39.552*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(39.576*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[154]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[154]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(39.792*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(39.816*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[155]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[155]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(39.984*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(40.008*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[156]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[156]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(40.224*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(40.248*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[157]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[157]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(40.464*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(40.488*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[158]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[158]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(40.656*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(40.68*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[159]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[159]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(40.896*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(40.92*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[15]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[15]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(9.36*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(9.384*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[160]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[160]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(41.088*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(41.12*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[161]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[161]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(41.344*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(41.376*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[162]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[162]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(41.536*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(41.568*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[163]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[163]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(41.728*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(41.76*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[164]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[164]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(41.984*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(42.016*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[165]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[165]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(42.176*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(42.208*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[166]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[166]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(42.432*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(42.464*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[167]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[167]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(42.624*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(42.656*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[168]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[168]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(42.816*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(42.848*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[169]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[169]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(43.072*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(43.104*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[16]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[16]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(9.6*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(9.624*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[170]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[170]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(43.264*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(43.296*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[171]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[171]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(43.52*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(43.552*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[172]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[172]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(43.712*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(43.744*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[173]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[173]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(43.968*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(44.0*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[174]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[174]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(44.16*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(44.192*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[175]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[175]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(44.352*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(44.384*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[176]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[176]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(44.608*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(44.64*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[177]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[177]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(44.8*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(44.832*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[178]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[178]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(45.056*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(45.088*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[179]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[179]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(45.248*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(45.28*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[17]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[17]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(9.84*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(9.864*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[180]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[180]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(45.44*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(45.472*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[181]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[181]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(45.696*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(45.728*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[182]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[182]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(45.888*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(45.92*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[183]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[183]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(46.144*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(46.176*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[184]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[184]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(46.336*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(46.368*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[185]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[185]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(46.592*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(46.624*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[186]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[186]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(46.784*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(46.816*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[187]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[187]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(46.976*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(47.008*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[188]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[188]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(47.232*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(47.264*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[189]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[189]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(47.424*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(47.456*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[18]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[18]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(10.032*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(10.056*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[190]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[190]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(47.68*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(47.712*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[191]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[191]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(47.872*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(47.904*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[192]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[192]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(48.096*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(48.12*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[193]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[193]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(48.336*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(48.36*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[194]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[194]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(48.528*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(48.552*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[195]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[195]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(48.768*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(48.792*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[196]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[196]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(48.96*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(48.984*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[197]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[197]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(49.2*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(49.224*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[198]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[198]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(49.392*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(49.416*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[199]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[199]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(49.632*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(49.656*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[19]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[19]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(10.272*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(10.296*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[1]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[1]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(6.336*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(6.36*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[200]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[200]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(49.824*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(49.848*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[201]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[201]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(50.064*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(50.088*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[202]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[202]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(50.304*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(50.328*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[203]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[203]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(50.496*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(50.52*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[204]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[204]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(50.736*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(50.76*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[205]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[205]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(50.928*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(50.952*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[206]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[206]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(51.168*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(51.192*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[207]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[207]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(51.36*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(51.384*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[208]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[208]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(51.6*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(51.624*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[209]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[209]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(51.84*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(51.864*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[20]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[20]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(10.464*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(10.488*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[210]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[210]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(52.032*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(52.056*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[211]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[211]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(52.272*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(52.296*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[212]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[212]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(52.464*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(52.488*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[213]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[213]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(52.704*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(52.728*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[214]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[214]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(52.896*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(52.92*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[215]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[215]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(53.136*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(53.16*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[216]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[216]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(53.328*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(53.352*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[217]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[217]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(53.568*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(53.592*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[218]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[218]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(53.808*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(53.832*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[219]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[219]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(54.0*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(54.024*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[21]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[21]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(10.704*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(10.728*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[220]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[220]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(54.24*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(54.264*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[221]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[221]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(54.432*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(54.456*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[222]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[222]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(54.672*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(54.696*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[223]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[223]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(54.864*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(54.888*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[224]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[224]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(55.104*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(55.136*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[225]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[225]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(55.296*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(55.328*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[226]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[226]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(55.552*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(55.584*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[227]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[227]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(55.744*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(55.776*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[228]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[228]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(56.0*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(56.032*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[229]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[229]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(56.192*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(56.224*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[22]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[22]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(10.896*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(10.92*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[230]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[230]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(56.384*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(56.416*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[231]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[231]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(56.64*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(56.672*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[232]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[232]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(56.832*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(56.864*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[233]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[233]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(57.088*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(57.12*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[234]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[234]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(57.28*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(57.312*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[235]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[235]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(57.472*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(57.504*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[236]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[236]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(57.728*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(57.76*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[237]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[237]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(57.92*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(57.952*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[238]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[238]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(58.176*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(58.208*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[239]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[239]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(58.368*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(58.4*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[23]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[23]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(11.136*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(11.16*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[240]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[240]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(58.624*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(58.656*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[241]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[241]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(58.816*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(58.848*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[242]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[242]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(59.008*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(59.04*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[243]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[243]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(59.264*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(59.296*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[244]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[244]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(59.456*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(59.488*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[245]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[245]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(59.712*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(59.744*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[246]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[246]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(59.904*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(59.936*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[247]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[247]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(60.096*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(60.128*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[248]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[248]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(60.352*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(60.384*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[249]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[249]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(60.544*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(60.576*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[24]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[24]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(11.328*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(11.352*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[250]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[250]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(60.8*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(60.832*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[251]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[251]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(60.992*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(61.024*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[252]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[252]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(61.248*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(61.28*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[253]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[253]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(61.44*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(61.472*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[254]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[254]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(61.632*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(61.664*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[255]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[255]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(61.888*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(61.92*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[25]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[25]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(11.568*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(11.592*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[26]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[26]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(11.808*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(11.832*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[27]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[27]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(12.0*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(12.024*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[28]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[28]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(12.24*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(12.264*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[29]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[29]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(12.432*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(12.456*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[2]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[2]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(6.528*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(6.552*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[30]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[30]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(12.672*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(12.696*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[31]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[31]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(12.864*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(12.888*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[32]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[32]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(13.12*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(13.152*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[33]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[33]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(13.312*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(13.344*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[34]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[34]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(13.504*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(13.536*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[35]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[35]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(13.76*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(13.792*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[36]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[36]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(13.952*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(13.984*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[37]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[37]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(14.208*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(14.24*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[38]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[38]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(14.4*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(14.432*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[39]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[39]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(14.656*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(14.688*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[3]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[3]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(6.768*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(6.792*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[40]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[40]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(14.848*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(14.88*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[41]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[41]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(15.04*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(15.072*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[42]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[42]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(15.296*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(15.328*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[43]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[43]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(15.488*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(15.52*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[44]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[44]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(15.744*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(15.776*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[45]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[45]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(15.936*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(15.968*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[46]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[46]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(16.128*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(16.16*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[47]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[47]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(16.384*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(16.416*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[48]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[48]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(16.576*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(16.608*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[49]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[49]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(16.832*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(16.864*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[4]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[4]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(6.96*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(6.984*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[50]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[50]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(17.024*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(17.056*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[51]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[51]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(17.28*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(17.312*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[52]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[52]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(17.472*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(17.504*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[53]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[53]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(17.664*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(17.696*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[54]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[54]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(17.92*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(17.952*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[55]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[55]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(18.112*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(18.144*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[56]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[56]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(18.368*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(18.4*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[57]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[57]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(18.56*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(18.592*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[58]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[58]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(18.752*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(18.784*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[59]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[59]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(19.008*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(19.04*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[5]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[5]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(7.2*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(7.224*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[60]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[60]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(19.2*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(19.232*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[61]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[61]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(19.456*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(19.488*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[62]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[62]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(19.648*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(19.68*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[63]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[63]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(19.904*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(19.936*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[64]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[64]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(20.112*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(20.136*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[65]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[65]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(20.304*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(20.328*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[66]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[66]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(20.544*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(20.568*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[67]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[67]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(20.736*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(20.76*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[68]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[68]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(20.976*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(21.0*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[69]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[69]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(21.168*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(21.192*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[6]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[6]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(7.392*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(7.416*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[70]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[70]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(21.408*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(21.432*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[71]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[71]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(21.648*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(21.672*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[72]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[72]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(21.84*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(21.864*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[73]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[73]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(22.08*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(22.104*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[74]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[74]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(22.272*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(22.296*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[75]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[75]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(22.512*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(22.536*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[76]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[76]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(22.704*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(22.728*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[77]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[77]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(22.944*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(22.968*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[78]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[78]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(23.184*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(23.208*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[79]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[79]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(23.376*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(23.4*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[7]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[7]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(7.632*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(7.656*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[80]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[80]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(23.616*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(23.64*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[81]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[81]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(23.808*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(23.832*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[82]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[82]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(24.048*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(24.072*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[83]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[83]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(24.24*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(24.264*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[84]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[84]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(24.48*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(24.504*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[85]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[85]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(24.672*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(24.696*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[86]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[86]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(24.912*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(24.936*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[87]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[87]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(25.152*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(25.176*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[88]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[88]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(25.344*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(25.368*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[89]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[89]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(25.584*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(25.608*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[8]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[8]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(7.824*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(7.848*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[90]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[90]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(25.776*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(25.8*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[91]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[91]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(26.016*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(26.04*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[92]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[92]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(26.208*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(26.232*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[93]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[93]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(26.448*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(26.472*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[94]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[94]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(26.64*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(26.664*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[95]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[95]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(26.88*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(26.904*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[96]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[96]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(27.072*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(27.104*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[97]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[97]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(27.328*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(27.36*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[98]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[98]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(27.52*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(27.552*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[99]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[99]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(27.776*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(27.808*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {w_d[9]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin w_d[9]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(8.064*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(8.088*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[0]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[0]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(78.096*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(78.12*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[100]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[100]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(95.232*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(95.264*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[101]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[101]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(95.424*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(95.456*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[102]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[102]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(95.616*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(95.648*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[103]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[103]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(95.744*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(95.776*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[104]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[104]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(95.936*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(95.968*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[105]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[105]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(96.128*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(96.16*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[106]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[106]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(96.32*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(96.352*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[107]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[107]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(96.448*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(96.48*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[108]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[108]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(96.64*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(96.672*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[109]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[109]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(96.832*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(96.864*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[10]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[10]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(79.776*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(79.8*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[110]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[110]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(96.96*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(96.992*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[111]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[111]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(97.152*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(97.184*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[112]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[112]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(97.344*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(97.376*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[113]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[113]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(97.472*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(97.504*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[114]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[114]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(97.664*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(97.696*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[115]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[115]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(97.856*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(97.888*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[116]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[116]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(97.984*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(98.016*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[117]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[117]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(98.176*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(98.208*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[118]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[118]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(98.368*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(98.4*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[119]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[119]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(98.496*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(98.528*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[11]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[11]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(79.968*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(79.992*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[120]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[120]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(98.688*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(98.72*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[121]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[121]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(98.88*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(98.912*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[122]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[122]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(99.008*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(99.04*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[123]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[123]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(99.2*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(99.232*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[124]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[124]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(99.392*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(99.424*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[125]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[125]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(99.584*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(99.616*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[126]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[126]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(99.712*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(99.744*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[127]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[127]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(99.904*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(99.936*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[12]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[12]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(80.16*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(80.184*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[13]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[13]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(80.304*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(80.328*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[14]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[14]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(80.496*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(80.52*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[15]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[15]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(80.64*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(80.664*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[16]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[16]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(80.832*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(80.856*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[17]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[17]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(80.976*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(81.0*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[18]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[18]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(81.168*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(81.192*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[19]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[19]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(81.36*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(81.384*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[1]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[1]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(78.24*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(78.264*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[20]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[20]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(81.504*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(81.528*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[21]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[21]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(81.696*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(81.72*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[22]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[22]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(81.84*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(81.864*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[23]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[23]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(82.032*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(82.056*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[24]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[24]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(82.176*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(82.2*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[25]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[25]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(82.368*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(82.392*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[26]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[26]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(82.56*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(82.584*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[27]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[27]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(82.704*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(82.728*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[28]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[28]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(82.896*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(82.92*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[29]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[29]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(83.04*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(83.064*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[2]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[2]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(78.432*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(78.456*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[30]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[30]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(83.232*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(83.256*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[31]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[31]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(83.424*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(83.448*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[32]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[32]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(83.584*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(83.616*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[33]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[33]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(83.712*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(83.744*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[34]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[34]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(83.904*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(83.936*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[35]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[35]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(84.096*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(84.128*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[36]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[36]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(84.288*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(84.32*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[37]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[37]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(84.416*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(84.448*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[38]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[38]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(84.608*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(84.64*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[39]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[39]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(84.8*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(84.832*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[3]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[3]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(78.576*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(78.6*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[40]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[40]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(84.928*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(84.96*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[41]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[41]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(85.12*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(85.152*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[42]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[42]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(85.312*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(85.344*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[43]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[43]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(85.44*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(85.472*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[44]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[44]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(85.632*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(85.664*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[45]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[45]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(85.824*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(85.856*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[46]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[46]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(85.952*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(85.984*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[47]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[47]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(86.144*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(86.176*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[48]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[48]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(86.336*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(86.368*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[49]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[49]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(86.464*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(86.496*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[4]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[4]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(78.768*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(78.792*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[50]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[50]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(86.656*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(86.688*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[51]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[51]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(86.848*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(86.88*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[52]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[52]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(86.976*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(87.008*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[53]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[53]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(87.168*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(87.2*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[54]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[54]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(87.36*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(87.392*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[55]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[55]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(87.552*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(87.584*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[56]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[56]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(87.68*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(87.712*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[57]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[57]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(87.872*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(87.904*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[58]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[58]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(88.064*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(88.096*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[59]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[59]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(88.192*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(88.224*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[5]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[5]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(78.912*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(78.936*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[60]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[60]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(88.384*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(88.416*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[61]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[61]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(88.576*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(88.608*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[62]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[62]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(88.704*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(88.736*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[63]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[63]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(88.896*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(88.928*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[64]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[64]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(89.088*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(89.112*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[65]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[65]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(89.232*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(89.256*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[66]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[66]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(89.424*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(89.448*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[67]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[67]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(89.568*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(89.592*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[68]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[68]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(89.76*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(89.784*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[69]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[69]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(89.952*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(89.976*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[6]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[6]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(79.104*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(79.128*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[70]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[70]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(90.096*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(90.12*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[71]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[71]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(90.288*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(90.312*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[72]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[72]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(90.432*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(90.456*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[73]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[73]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(90.624*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(90.648*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[74]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[74]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(90.816*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(90.84*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[75]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[75]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(90.96*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(90.984*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[76]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[76]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(91.152*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(91.176*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[77]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[77]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(91.296*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(91.32*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[78]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[78]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(91.488*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(91.512*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[79]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[79]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(91.632*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(91.656*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[7]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[7]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(79.296*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(79.32*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[80]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[80]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(91.824*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(91.848*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[81]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[81]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(92.016*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(92.04*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[82]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[82]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(92.16*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(92.184*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[83]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[83]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(92.352*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(92.376*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[84]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[84]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(92.496*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(92.52*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[85]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[85]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(92.688*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(92.712*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[86]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[86]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(92.832*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(92.856*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[87]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[87]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(93.024*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(93.048*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[88]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[88]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(93.216*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(93.24*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[89]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[89]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(93.36*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(93.384*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[8]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[8]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(79.44*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(79.464*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[90]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[90]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(93.552*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(93.576*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[91]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[91]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(93.696*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(93.72*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[92]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[92]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(93.888*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(93.912*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[93]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[93]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(94.08*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(94.104*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[94]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[94]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(94.224*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(94.248*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[95]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[95]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(94.416*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(94.44*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[96]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[96]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(94.592*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(94.624*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[97]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[97]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(94.72*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(94.752*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[98]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[98]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(94.912*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(94.944*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[99]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[99]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M6] [expr {round(99.722*$lsl_dbu)}] [expr {round(95.104*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(95.136*$lsl_dbu)}]
set lsl_bt [$lsl_block findBTerm {x_d[9]}]
if {$lsl_bt == "NULL"} {error "missing assigned pin x_d[9]"}
foreach lsl_old [$lsl_bt getBPins] {odb::dbBPin_destroy $lsl_old}
set lsl_bp [odb::dbBPin_create $lsl_bt]
$lsl_bp setPlacementStatus FIRM
odb::dbBox_create $lsl_bp [$lsl_tech findLayer M4] [expr {round(99.708*$lsl_dbu)}] [expr {round(79.632*$lsl_dbu)}] [expr {round(99.792*$lsl_dbu)}] [expr {round(79.656*$lsl_dbu)}]
