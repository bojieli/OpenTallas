# el1011-q-tile 2026-10-11: PRE_GLOBAL_PLACE for the tile rebuild = ROM capture / request flops at the macro pins (when the block
# has ROM macros) + every IO pin flop at its die pin (common_flow/io_flop_at_pins.tcl; rpxc FF I2R window 710 = li/xl/n_a/n_b/ib pin flops
# left in the logic under a 138k-sink tree).  Placement only.
set ot_has_rom 0
foreach ot_m [[ord::get_db_block] getInsts] { if {[[$ot_m getMaster] isBlock] && [string match "ot_rom_*" [[$ot_m getMaster] getName]]} { set ot_has_rom 1; break } }
if {$ot_has_rom} { source /src/physical/qwen_die_masters/rom_cap_at_pins.tcl }
source /src/physical/common_flow/io_flop_at_pins.tcl
