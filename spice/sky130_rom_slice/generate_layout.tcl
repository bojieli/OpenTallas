# Generate a deliberately roomy, inspectable two-column SKY130 ROM slice.
# The present and absent columns are identical except for one via1.

proc ot_box {x1 y1 x2 y2} {
    box values ${x1}um ${y1}um ${x2}um ${y2}um
}

proc ot_paint {layer x1 y1 x2 y2} {
    ot_box $x1 $y1 $x2 $y2
    paint $layer
}

proc ot_via1 {x y} {
    set x1 [expr {$x - 0.13}]
    set y1 [expr {$y - 0.13}]
    set x2 [expr {$x + 0.13}]
    set y2 [expr {$y + 0.13}]
    ot_box $x1 $y1 $x2 $y2
    sky130::via1_draw
}

proc ot_via2 {x y} {
    set x1 [expr {$x - 0.14}]
    set y1 [expr {$y - 0.14}]
    set x2 [expr {$x + 0.14}]
    set y2 [expr {$y + 0.14}]
    ot_box $x1 $y1 $x2 $y2
    sky130::via2_draw
}

proc ot_nfet {name x y} {
    ot_box $x $y $x $y
    magic::gencell sky130::sky130_fd_pr__nfet_01v8 $name \
        w 1.0 l 0.15 guard 1 full_metal 1 viagb 100 topc 1 botc 0 doports 1
    set child [instance list celldef $name]
    set ::ot_nfet_cell $child
    if {![file exists ${child}.mag]} {
        pushstack $child
        save $child
        popstack
    }
}

proc ot_pfet {name x y} {
    ot_box $x $y $x $y
    magic::gencell sky130::sky130_fd_pr__pfet_01v8 $name \
        w 1.0 l 0.15 guard 1 full_metal 1 viagb 100 topc 1 botc 0 doports 1
    set child [instance list celldef $name]
    set ::ot_pfet_cell $child
    if {![file exists ${child}.mag]} {
        pushstack $child
        save $child
        popstack
    }
}

proc ot_port {name index layer x1 y1 x2 y2} {
    ot_box $x1 $y1 $x2 $y2
    label $name center $layer
    port make $index
}

proc ot_column {prefix base programmed port_base} {
    set xrow [expr {$base + 2.0}]
    set xmask [expr {$base + 6.0}]
    set xsense [expr {$base + 10.0}]
    set xbl [expr {$xrow + 0.57}]
    set xrow_g [expr {$xrow + 0.79}]
    set xmask_g [expr {$xmask + 0.79}]
    set xsense_d [expr {$xsense + 0.57}]
    set xsense_g [expr {$xsense + 0.79}]

    ot_nfet NROW_${prefix} $xrow 2.0
    ot_nfet NMASK_${prefix} $xmask 2.0
    ot_nfet NSENSE_${prefix} $xsense 2.0
    ot_pfet PPRE_${prefix} $xrow 8.0
    ot_pfet PSENSE_${prefix} $xsense 8.0

    # Series row-select and expert-enable discharge devices.
    ot_paint metal1 [expr {$xrow + 0.95}] 2.99 [expr {$xmask + 0.69}] 3.28

    # Ground the mask-device and sense-device sources through their body rail.
    ot_paint metal1 [expr {$xmask + 0.90}] 1.90 [expr {$xmask + 1.12}] 3.45
    ot_paint metal1 [expr {$xsense + 0.90}] 1.90 [expr {$xsense + 1.12}] 3.45

    # Tie precharge/sense PMOS sources to their n-well body rail.
    ot_paint metal1 [expr {$xrow + 0.90}] 7.90 [expr {$xrow + 1.12}] 9.45
    ot_paint metal1 [expr {$xsense + 0.90}] 7.90 [expr {$xsense + 1.12}] 9.45

    # Physical bitline.  Only the programmed column receives the lower via1.
    ot_paint metal1 [expr {$xbl - 0.15}] 2.99 [expr {$xbl + 0.15}] 3.28
    ot_paint metal2 [expr {$xbl - 0.15}] 2.95 [expr {$xbl + 0.15}] 10.15
    if {$programmed} {
        ot_via1 $xbl 3.13
    }
    ot_via1 $xbl 9.155

    # Both CMOS sense gates read the physical bitline.
    ot_via1 $xsense_g 3.905
    ot_paint metal2 $xbl 3.755 $xsense_g 4.055
    ot_via1 $xsense_g 9.975
    ot_paint metal2 $xbl 9.825 $xsense_g 10.125

    # Sense output uses M3 so it can cross the M2 gate/bitline wiring.
    ot_via1 $xsense_d 3.13
    ot_via2 $xsense_d 3.13
    ot_via1 $xsense_d 9.155
    ot_via2 $xsense_d 9.155
    ot_paint metal3 [expr {$xsense_d - 0.17}] 2.99 [expr {$xsense_d + 0.17}] 9.33
    ot_paint metal3 $xsense_d 8.99 [expr {$xsense + 1.65}] 9.33

    # Decoder and precharge controls stay on M1; M2 may cross without a via.
    ot_paint metal1 [expr {$base + 0.50}] 3.78 [expr {$xrow_g + 0.15}] 4.06
    ot_paint metal1 [expr {$xmask_g - 0.15}] 3.78 [expr {$xmask + 2.30}] 4.06
    ot_paint metal1 [expr {$base + 0.50}] 9.84 [expr {$xrow_g + 0.15}] 10.11

    ot_port WL_${prefix} $port_base metal1 [expr {$base + 0.55}] 3.82 [expr {$base + 1.35}] 4.02
    ot_port EN_${prefix} [expr {$port_base + 1}] metal1 [expr {$xmask + 1.30}] 3.82 [expr {$xmask + 2.20}] 4.02
    ot_port PRE_${prefix} [expr {$port_base + 2}] metal1 [expr {$base + 0.55}] 9.87 [expr {$base + 1.35}] 10.07
    ot_port Q_${prefix} [expr {$port_base + 3}] metal3 [expr {$xsense + 1.25}] 9.04 [expr {$xsense + 1.60}] 9.28

    # Internal names make the extracted topology and programming distinction auditable.
    ot_box [expr {$xbl - 0.10}] 6.30 [expr {$xbl + 0.10}] 6.70
    label BL_${prefix} center metal2
    if {!$programmed} {
        ot_box [expr {$xrow + 0.47}] 3.02 [expr {$xrow + 0.67}] 3.25
        label ROM_DRAIN_ABSENT center metal1
    }
}

load sky130_rom_slice -silent
units internal
snap internal
random seed 12345

# Shared physical substrate/body rails.
ot_paint metal1 0.50 1.88 31.80 2.12
ot_paint metal1 0.50 7.88 31.80 8.12

ot_column PRESENT 0.0 1 3
ot_column ABSENT 18.0 0 7

ot_port VGND 1 metal1 0.60 1.90 1.40 2.10
ot_port VPWR 2 metal1 0.60 7.90 1.40 8.10

# Deterministic boundary and top-level database.
ot_paint comment 0.00 0.00 32.50 11.50
property FIXED_BBOX {0 0 6500 2300}
set ot_child_timestamp [cellname timestamp $::ot_nfet_cell]
set ot_pfet_timestamp [cellname timestamp $::ot_pfet_cell]
if {$ot_pfet_timestamp > $ot_child_timestamp} {
    set ot_child_timestamp $ot_pfet_timestamp
}
cellname timestamp sky130_rom_slice [expr {$ot_child_timestamp + 1}]
save sky130_rom_slice

drc check
drc catchup
puts "OT_DRC_COUNT_BEGIN"
drc count total
puts "OT_DRC_DETAILS=[drc listall why]"
puts "OT_DRC_COUNT_END"

gds write sky130_rom_slice
extract path .
extract all
ext2spice lvs
ext2spice hierarchy off
# Keep the extracted transistor network flat, but force a top-level wrapper so
# Netgen can compare the declared physical ports rather than treating them as
# ordinary top-level nodes.  Netgen returns zero even for pin-match failures,
# so the governed runner also parses the final LVS verdict.
ext2spice subcircuit on
ext2spice subcircuit top on
ext2spice -o sky130_rom_slice.extracted.spice sky130_rom_slice.ext

# Emit a second, capacitance-preserving netlist for the extracted electrical
# campaign.  Detailed interconnect resistance is not implied here: the base
# extractor supplies device and coupling capacitance, while a later extresist
# campaign is a separate sign-off gate.
ext2spice cthresh 0
ext2spice -o sky130_rom_slice.pex.spice sky130_rom_slice.ext
quit -noprompt
