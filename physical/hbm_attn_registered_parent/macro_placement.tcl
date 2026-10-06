# Native R0 pin-grid alignment within the same selected slot; retain >=5um boundary halo.
# Turing service-attn-r1 existing 4x4 allocation, no placement rescaling.
place_macro -macro_name {u_tile/registered_parent.row\[0\].head\[0\].u_g} -location {5.04 5.04} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[0\].head\[1\].u_g} -location {352.992 5.04} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[0\].head\[2\].u_g} -location {700.992 5.04} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[0\].head\[3\].u_g} -location {1048.992 5.04} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[1\].head\[0\].u_g} -location {5.04 352.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[1\].head\[1\].u_g} -location {352.992 352.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[1\].head\[2\].u_g} -location {700.992 352.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[1\].head\[3\].u_g} -location {1048.992 352.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[2\].head\[0\].u_g} -location {5.04 700.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[2\].head\[1\].u_g} -location {352.992 700.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[2\].head\[2\].u_g} -location {700.992 700.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[2\].head\[3\].u_g} -location {1048.992 700.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[3\].head\[0\].u_g} -location {5.04 1048.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[3\].head\[1\].u_g} -location {352.992 1048.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[3\].head\[2\].u_g} -location {700.992 1048.992} -orientation R0 -exact
place_macro -macro_name {u_tile/registered_parent.row\[3\].head\[3\].u_g} -location {1048.992 1048.992} -orientation R0 -exact

# Retain the selected allocation while the vendor placer processes remaining logic.
set ot_block [ord::get_db_block]
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[0\].head\[0\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 0 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[0\].head\[1\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 1 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[0\].head\[2\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 2 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[0\].head\[3\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 3 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[1\].head\[0\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 4 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[1\].head\[1\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 5 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[1\].head\[2\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 6 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[1\].head\[3\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 7 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[2\].head\[0\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 8 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[2\].head\[1\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 9 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[2\].head\[2\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 10 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[2\].head\[3\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 11 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[3\].head\[0\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 12 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[3\].head\[1\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 13 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[3\].head\[2\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 14 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
set ot_macro [$ot_block findInst {u_tile/registered_parent.row\[3\].head\[3\].u_g}]
if {$ot_macro == "NULL"} {error "Missing head 15 in full H16 tile"}
$ot_macro setPlacementStatus FIRM
