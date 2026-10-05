# Produce a separate full-RC netlist from the governed archived SKY130 slice.
# This script never modifies or replaces the capacitance-only physical artifact.

load sky130_rom_slice -silent
random seed 12345
extract path .
if {[info exists ::env(OPENTALLAS_RC_STYLE)]} {
    set ot_rc_style $::env(OPENTALLAS_RC_STYLE)
} else {
    set ot_rc_style {ngspice()}
}
extract style $ot_rc_style

# Configure the detailed extractor before using Magic's integrated one-pass
# `extract do extresist` flow.  Zero thresholds retain every eligible network
# and every resistor segment; simplification is disabled for auditability.
extresist threshold 0
extresist mindelay 0
extresist minres 0
extresist simplify off
extresist extout on
extresist lumped on
extresist silent off

puts "OT_EXTRESIST_SETTINGS_BEGIN"
puts "OT_EXTRESIST_THRESHOLD_MOHM=[extresist threshold]"
puts "OT_EXTRESIST_MINDELAY_PS=[extresist mindelay]"
puts "OT_EXTRESIST_MINRES_MOHM=[extresist minres]"
puts "OT_EXTRESIST_SIMPLIFY=off"
puts "OT_EXTRACT_INTEGRATED_EXTRESIST=on"
puts "OT_EXTRACTION_STYLE=$ot_rc_style"
puts "OT_EXTRESIST_SETTINGS_END"

extract do extresist
extract all

puts "OT_EXTRESIST_ARTIFACTS_BEGIN"
puts "OT_TOP_EXT=[file exists sky130_rom_slice.ext]"
puts "OT_TOP_RES_EXT=[file exists sky130_rom_slice.res.ext]"
puts "OT_EXTRESIST_ARTIFACTS_END"

ext2spice format ngspice
ext2spice hierarchy off
ext2spice subcircuit on
ext2spice subcircuit top on
ext2spice extresist on
ext2spice cthresh 0
ext2spice -o sky130_rom_slice.rc.pex.spice sky130_rom_slice.ext
quit -noprompt
