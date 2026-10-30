# Apply only to an own copied 3_place ODB. No netlist/cycle changes.
set ab [ord::get_db_block]
set au [$ab getDbUnitsPerMicron]
set ai [$ab findInst {u_fcore.g_bank[5].u_bank.wa_pin[8]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(156.87*$au)}] [expr {round(120.15*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[6].u_bank.read_data[17]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(116.64*$au)}] [expr {round(178.2*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[8].u_bank.wa_pin[2]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(219.726*$au)}] [expr {round(127.17*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[5].u_bank.wa_pin[2]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(217.998*$au)}] [expr {round(101.52*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[6].u_bank.read_data[30]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(105.516*$au)}] [expr {round(182.79*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[6].u_bank.read_data[28]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(120.744*$au)}] [expr {round(184.68*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[2].u_bank.wa_pin[0]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(189.756*$au)}] [expr {round(71.01*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[9].u_bank.a_pin[6]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(63.612*$au)}] [expr {round(182.79*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[6].u_bank.read_data[31]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(118.53*$au)}] [expr {round(168.48*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[9].u_bank.wd_pin[22]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(218.808*$au)}] [expr {round(164.97*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[9].u_bank.wd_pin[15]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(224.208*$au)}] [expr {round(162.54*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[9].u_bank.wd_pin[14]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(217.026*$au)}] [expr {round(160.92*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[8].u_bank.wa_pin[0]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(219.672*$au)}] [expr {round(134.19*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[8].u_bank.wa_pin[1]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(217.998*$au)}] [expr {round(130.41*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[2].u_bank.wa_pin[2]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(190.89*$au)}] [expr {round(68.58*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[2].u_bank.wa_pin[1]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(192.618*$au)}] [expr {round(74.52*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[9].u_bank.a_pin[7]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(60.21*$au)}] [expr {round(183.06*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[9].u_bank.a_pin[5]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(61.668*$au)}] [expr {round(183.06*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[5].u_bank.wa_pin[1]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(216.702*$au)}] [expr {round(97.74*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[5].u_bank.wa_pin[0]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(217.026*$au)}] [expr {round(108.0*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[9].u_bank.a_pin[8]$_DFF_P_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(60.372*$au)}] [expr {round(183.6*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[8].u_bank.u_data.g_read[0].ks[1]$_DFFE_PP_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(127.332*$au)}] [expr {round(129.33*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[7].u_bank.u_data.g_read[0].ks[2]$_DFFE_PP_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(126.846*$au)}] [expr {round(137.16*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[7].u_bank.u_data.g_read[0].ks[0]$_DFFE_PP_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(126.63*$au)}] [expr {round(136.89*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[8].u_bank.u_data.g_read[0].ks[2]$_DFFE_PP_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(135.324*$au)}] [expr {round(137.7*$au)}]
$ai setPlacementStatus FIRM
set ai [$ab findInst {u_fcore.g_bank[8].u_bank.u_data.g_read[0].ks[0]$_DFFE_PP_}]
if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}
$ai setLocation [expr {round(135.648*$au)}] [expr {round(137.16*$au)}]
$ai setPlacementStatus FIRM
detailed_placement
check_placement -verbose
