set block [ord::get_db_block]
set scale [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])/1000.0}]
set inst [$block findInst sink_0]
if {$inst == "NULL"} {error "Missing actual fixed instance sink_0"}
if {[[$inst getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {error "Master changed sink_0"}
$inst setOrient R0
$inst setLocation [expr {round(2160*$scale)}] [expr {round(2160*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst sink_1]
if {$inst == "NULL"} {error "Missing actual fixed instance sink_1"}
if {[[$inst getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {error "Master changed sink_1"}
$inst setOrient R0
$inst setLocation [expr {round(5130*$scale)}] [expr {round(2160*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst sink_2]
if {$inst == "NULL"} {error "Missing actual fixed instance sink_2"}
if {[[$inst getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {error "Master changed sink_2"}
$inst setOrient R0
$inst setLocation [expr {round(8100*$scale)}] [expr {round(2160*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst sink_3]
if {$inst == "NULL"} {error "Missing actual fixed instance sink_3"}
if {[[$inst getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {error "Master changed sink_3"}
$inst setOrient R0
$inst setLocation [expr {round(11070*$scale)}] [expr {round(2160*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst sink_4]
if {$inst == "NULL"} {error "Missing actual fixed instance sink_4"}
if {[[$inst getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {error "Master changed sink_4"}
$inst setOrient R0
$inst setLocation [expr {round(14040*$scale)}] [expr {round(2160*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst sink_5]
if {$inst == "NULL"} {error "Missing actual fixed instance sink_5"}
if {[[$inst getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {error "Master changed sink_5"}
$inst setOrient R0
$inst setLocation [expr {round(17010*$scale)}] [expr {round(2160*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst sink_6]
if {$inst == "NULL"} {error "Missing actual fixed instance sink_6"}
if {[[$inst getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {error "Master changed sink_6"}
$inst setOrient R0
$inst setLocation [expr {round(19980*$scale)}] [expr {round(2160*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst sink_7]
if {$inst == "NULL"} {error "Missing actual fixed instance sink_7"}
if {[[$inst getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {error "Master changed sink_7"}
$inst setOrient R0
$inst setLocation [expr {round(22950*$scale)}] [expr {round(2160*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst source_buf]
if {$inst == "NULL"} {error "Missing actual fixed instance source_buf"}
if {[[$inst getMaster] getName] ne "BUFx4_ASAP7_75t_R"} {error "Master changed source_buf"}
$inst setOrient MX
$inst setLocation [expr {round(2322*$scale)}] [expr {round(2430*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst relay_0]
if {$inst == "NULL"} {error "Missing actual fixed instance relay_0"}
if {[[$inst getMaster] getName] ne "BUFx4_ASAP7_75t_R"} {error "Master changed relay_0"}
$inst setOrient MX
$inst setLocation [expr {round(2700*$scale)}] [expr {round(2430*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst relay_1]
if {$inst == "NULL"} {error "Missing actual fixed instance relay_1"}
if {[[$inst getMaster] getName] ne "BUFx4_ASAP7_75t_R"} {error "Master changed relay_1"}
$inst setOrient MX
$inst setLocation [expr {round(3078*$scale)}] [expr {round(2430*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst relay_2]
if {$inst == "NULL"} {error "Missing actual fixed instance relay_2"}
if {[[$inst getMaster] getName] ne "BUFx4_ASAP7_75t_R"} {error "Master changed relay_2"}
$inst setOrient MX
$inst setLocation [expr {round(3456*$scale)}] [expr {round(2430*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst relay_3]
if {$inst == "NULL"} {error "Missing actual fixed instance relay_3"}
if {[[$inst getMaster] getName] ne "BUFx4_ASAP7_75t_R"} {error "Master changed relay_3"}
$inst setOrient MX
$inst setLocation [expr {round(3834*$scale)}] [expr {round(2430*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst relay_4]
if {$inst == "NULL"} {error "Missing actual fixed instance relay_4"}
if {[[$inst getMaster] getName] ne "BUFx4_ASAP7_75t_R"} {error "Master changed relay_4"}
$inst setOrient MX
$inst setLocation [expr {round(4212*$scale)}] [expr {round(2430*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst relay_5]
if {$inst == "NULL"} {error "Missing actual fixed instance relay_5"}
if {[[$inst getMaster] getName] ne "BUFx4_ASAP7_75t_R"} {error "Master changed relay_5"}
$inst setOrient MX
$inst setLocation [expr {round(4590*$scale)}] [expr {round(2430*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst relay_6]
if {$inst == "NULL"} {error "Missing actual fixed instance relay_6"}
if {[[$inst getMaster] getName] ne "BUFx4_ASAP7_75t_R"} {error "Master changed relay_6"}
$inst setOrient MX
$inst setLocation [expr {round(4968*$scale)}] [expr {round(2430*$scale)}]
$inst setPlacementStatus LOCKED
set inst [$block findInst relay_7]
if {$inst == "NULL"} {error "Missing actual fixed instance relay_7"}
if {[[$inst getMaster] getName] ne "BUFx4_ASAP7_75t_R"} {error "Master changed relay_7"}
$inst setOrient MX
$inst setLocation [expr {round(5346*$scale)}] [expr {round(2430*$scale)}]
$inst setPlacementStatus LOCKED
set_dont_touch [get_cells *]
set_dont_touch [get_nets *]
puts "DS_NATIVE_RELAY_FIXED_CENSUS_17"
