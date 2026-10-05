# Generate a deliberately roomy, inspectable two-column IHP SG13G2 ROM slice.
# The present and absent columns are matched except for one top-level via1.

proc ot_box {x1 y1 x2 y2} {
    box values ${x1}um ${y1}um ${x2}um ${y2}um
}

proc ot_paint {layer x1 y1 x2 y2} {
    ot_box $x1 $y1 $x2 $y2
    paint $layer
}

proc ot_via1 {x y} {
    # Use 0.22 um rather than the mathematical 0.20-um minimum so Tcl
    # floating-point conversion cannot snap the box one grid point short.
    set x1 [expr {$x - 0.11}]
    set y1 [expr {$y - 0.11}]
    set x2 [expr {$x + 0.11}]
    set y2 [expr {$y + 0.11}]
    ot_box $x1 $y1 $x2 $y2
    units internal
    sg13g2::via1_draw
    units microns
}

proc ot_via2 {x y} {
    set x1 [expr {$x - 0.11}]
    set y1 [expr {$y - 0.11}]
    set x2 [expr {$x + 0.11}]
    set y2 [expr {$y + 0.11}]
    ot_box $x1 $y1 $x2 $y2
    units internal
    sg13g2::via2_draw
    units microns
}

proc ot_nfet {name x y} {
    ot_box $x $y $x $y
    # IHP's native generator normally raises contacted terminals to M2.  Keep
    # all terminals on M1 so that the top-level via1 is the programming mask.
    magic::gencell sg13g2::sg13_lv_nmos $name \
        w 1.0 l 0.13 guard 0 full_metal 0 \
        viasrc 0 viadrn 0 viagate 0 viagb 0 \
        topc 1 botc 0 doports 1
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
    magic::gencell sg13g2::sg13_lv_pmos $name \
        w 1.0 l 0.13 guard 0 full_metal 0 \
        viasrc 0 viadrn 0 viagate 0 viagb 0 \
        topc 1 botc 0 doports 1
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

proc ot_psub_tap {x y} {
    # A regular substrate tie is not an extracted resistor device.  Draw the
    # diffusion, contact, and M1 enclosure explicitly from the public rules.
    ot_paint psubdiff [expr {$x - 0.25}] [expr {$y - 0.25}] \
        [expr {$x + 0.25}] [expr {$y + 0.25}]
    ot_paint psubdiffcont [expr {$x - 0.08}] [expr {$y - 0.08}] \
        [expr {$x + 0.08}] [expr {$y + 0.08}]
    ot_paint metal1 [expr {$x - 0.16}] [expr {$y - 0.16}] \
        [expr {$x + 0.16}] [expr {$y + 0.16}]
}

proc ot_nwell_tap {x y} {
    ot_paint nsubdiff [expr {$x - 0.25}] [expr {$y - 0.25}] \
        [expr {$x + 0.25}] [expr {$y + 0.25}]
    ot_paint nsubdiffcont [expr {$x - 0.08}] [expr {$y - 0.08}] \
        [expr {$x + 0.08}] [expr {$y + 0.08}]
    ot_paint metal1 [expr {$x - 0.16}] [expr {$y - 0.16}] \
        [expr {$x + 0.16}] [expr {$y + 0.16}]
}

proc ot_column {prefix base programmed port_base} {
    set xrow [expr {$base + 2.0}]
    set xmask [expr {$base + 6.0}]
    set xsense [expr {$base + 10.0}]

    # Native generated-cell terminal centers for the declared W/L and options.
    # Shift PMOS placement left by 0.31 um so its D/G/S centers align with the
    # corresponding NMOS centers despite the different native well bounding box.
    set xrow_d [expr {$xrow + 0.15}]
    set xbl [expr {$xrow - 0.50}]
    set xrow_s [expr {$xrow + 0.66}]
    set xrow_g [expr {$xrow + 0.405}]
    set xmask_d [expr {$xmask + 0.15}]
    set xmask_s [expr {$xmask + 0.66}]
    set xmask_g [expr {$xmask + 0.405}]
    set xsense_d [expr {$xsense + 0.15}]
    set xsense_s [expr {$xsense + 0.66}]
    set xsense_g [expr {$xsense + 0.405}]
    set xsense_remote [expr {$xsense - 0.50}]
    set yn_term 2.68
    set yn_gate 3.40
    set yp_term 8.81
    set yp_gate 9.53

    ot_nfet NROW_${prefix} $xrow 2.0
    ot_nfet NMASK_${prefix} $xmask 2.0
    ot_nfet NSENSE_${prefix} $xsense 2.0
    ot_pfet PPRE_${prefix} [expr {$xrow - 0.31}] 8.0
    ot_pfet PSENSE_${prefix} [expr {$xsense - 0.31}] 8.0

    # Series row-select and expert-enable discharge devices.
    ot_paint metal1 [expr {$xrow_s - 0.12}] 2.78 \
        [expr {$xmask_d + 0.12}] 3.02

    # Ground the mask-device and sense-device sources through their body rail.
    ot_paint metal1 [expr {$xmask_s - 0.12}] 0.78 \
        [expr {$xmask_s + 0.12}] 3.02
    ot_paint metal1 [expr {$xsense_s - 0.12}] 0.78 \
        [expr {$xsense_s + 0.12}] 3.02

    # Tie precharge/sense PMOS sources to their n-well body rail.
    ot_paint metal1 [expr {$xrow_s - 0.12}] 7.62 \
        [expr {$xrow_s + 0.12}] 8.93
    ot_paint metal1 [expr {$xsense_s - 0.12}] 7.62 \
        [expr {$xsense_s + 0.12}] 8.93

    # Route both row drains left to a remote via site. This is required by the
    # IHP M1/via enclosure pitch: placing a via directly on the native drain
    # would overlap the neighboring terminal. Only the programmed column gets
    # the lower via1; both columns get the precharge connection at the top.
    ot_paint metal1 [expr {$xbl - 0.13}] [expr {$yn_term - 0.12}] \
        [expr {$xrow_d + 0.13}] [expr {$yn_term + 0.12}]
    ot_paint metal1 [expr {$xbl - 0.13}] [expr {$yp_term - 0.12}] \
        [expr {$xrow_d + 0.13}] [expr {$yp_term + 0.12}]
    ot_paint metal2 [expr {$xbl - 0.12}] [expr {$yn_term - 0.12}] \
        [expr {$xbl + 0.12}] [expr {$yp_gate + 0.12}]
    if {$programmed} {
        ot_via1 $xbl $yn_term
    }
    ot_via1 $xbl $yp_term

    # Both CMOS sense gates read the physical bitline through remote via sites.
    # The M1 gate stubs use the exact legal 0.16-um generator landing width.
    ot_paint metal1 [expr {$xsense_remote - 0.13}] [expr {$yn_gate - 0.08}] \
        [expr {$xsense_g + 0.13}] [expr {$yn_gate + 0.08}]
    ot_via1 $xsense_remote $yn_gate
    ot_paint metal2 $xbl [expr {$yn_gate - 0.12}] \
        $xsense_remote [expr {$yn_gate + 0.12}]
    ot_paint metal1 [expr {$xsense_remote - 0.13}] [expr {$yp_gate - 0.08}] \
        [expr {$xsense_g + 0.13}] [expr {$yp_gate + 0.08}]
    ot_via1 $xsense_remote $yp_gate
    ot_paint metal2 $xbl [expr {$yp_gate - 0.12}] \
        $xsense_remote [expr {$yp_gate + 0.12}]

    # Sense output also escapes to a remote site before rising to M3. Dedicated
    # M2 landing patches meet the IHP 0.144-um^2 minimum-area rule.
    ot_paint metal1 [expr {$xsense_remote - 0.13}] [expr {$yn_term - 0.12}] \
        [expr {$xsense_d + 0.13}] [expr {$yn_term + 0.12}]
    ot_paint metal2 [expr {$xsense_remote - 0.31}] [expr {$yn_term - 0.13}] \
        [expr {$xsense_remote + 0.31}] [expr {$yn_term + 0.13}]
    ot_via1 $xsense_remote $yn_term
    ot_via2 $xsense_remote $yn_term
    ot_paint metal1 [expr {$xsense_remote - 0.13}] [expr {$yp_term - 0.12}] \
        [expr {$xsense_d + 0.13}] [expr {$yp_term + 0.12}]
    ot_paint metal2 [expr {$xsense_remote - 0.31}] [expr {$yp_term - 0.13}] \
        [expr {$xsense_remote + 0.31}] [expr {$yp_term + 0.13}]
    ot_via1 $xsense_remote $yp_term
    ot_via2 $xsense_remote $yp_term
    ot_paint metal3 [expr {$xsense_remote - 0.12}] [expr {$yn_term - 0.12}] \
        [expr {$xsense_remote + 0.12}] [expr {$yp_term + 0.12}]
    ot_paint metal3 $xsense_remote [expr {$yp_term - 0.12}] \
        [expr {$xsense + 1.70}] [expr {$yp_term + 0.12}]

    # Decoder and precharge controls stay on M1; M2 may cross without a via.
    ot_paint metal1 [expr {$base + 0.50}] [expr {$yn_gate - 0.08}] \
        [expr {$xrow_g + 0.13}] [expr {$yn_gate + 0.08}]
    ot_paint metal1 [expr {$xmask_g - 0.13}] [expr {$yn_gate - 0.08}] \
        [expr {$xmask + 2.30}] [expr {$yn_gate + 0.08}]
    ot_paint metal1 [expr {$base + 0.50}] [expr {$yp_gate - 0.08}] \
        [expr {$xrow_g + 0.13}] [expr {$yp_gate + 0.08}]

    ot_port WL_${prefix} $port_base metal1 \
        [expr {$base + 0.55}] [expr {$yn_gate - 0.07}] \
        [expr {$base + 1.35}] [expr {$yn_gate + 0.07}]
    ot_port EN_${prefix} [expr {$port_base + 1}] metal1 \
        [expr {$xmask + 1.30}] [expr {$yn_gate - 0.07}] \
        [expr {$xmask + 2.20}] [expr {$yn_gate + 0.07}]
    ot_port PRE_${prefix} [expr {$port_base + 2}] metal1 \
        [expr {$base + 0.55}] [expr {$yp_gate - 0.07}] \
        [expr {$base + 1.35}] [expr {$yp_gate + 0.07}]
    ot_port Q_${prefix} [expr {$port_base + 3}] metal3 \
        [expr {$xsense + 1.30}] 8.91 \
        [expr {$xsense + 1.65}] 9.09

    # Internal names make the extracted programming distinction auditable.
    ot_box [expr {$xbl - 0.10}] 6.30 [expr {$xbl + 0.10}] 6.70
    label BL_${prefix} center metal2
    if {!$programmed} {
        ot_box [expr {$xrow_d - 0.10}] [expr {$yn_term - 0.10}] \
            [expr {$xrow_d + 0.10}] [expr {$yn_term + 0.10}]
        label ROM_DRAIN_ABSENT center metal1
    }
}

load ihp_sg13g2_rom_slice -silent
units microns
snap internal
random seed 12345

# Shared physical substrate/body rails and explicit well region.  The native
# MOS generators use guard=0; these rule-spaced taps provide the body ties.
# Bridge only the native PMOS N-well vertical interval. Extending a blanket
# well beyond 9.62 um creates an implicit P-well/N-well overlap that base DRC
# does not flag but Magic's resistance extractor correctly rejects.
ot_paint nwell 0.40 8.00 32.10 9.62
# Local rule-enclosed pocket for the shared well tap, joined to the bridge.
ot_paint nwell 15.40 7.90 16.60 9.10
ot_paint metal1 0.50 0.66 31.80 0.90
ot_paint metal1 0.50 7.50 31.80 7.74
ot_psub_tap 16.00 0.78
ot_nwell_tap 16.00 8.40
ot_paint metal1 15.88 7.62 16.12 8.56

ot_column PRESENT 0.0 1 3
ot_column ABSENT 18.0 0 7

ot_port VGND 1 metal1 0.60 0.69 1.40 0.87
ot_port VPWR 2 metal1 0.60 7.53 1.40 7.71

# Deterministic boundary and top-level database.
ot_paint comment 0.00 0.00 32.50 11.50
units internal
property FIXED_BBOX {0 0 6500 2300}
units microns
set ot_child_timestamp [cellname timestamp $::ot_nfet_cell]
set ot_pfet_timestamp [cellname timestamp $::ot_pfet_cell]
if {$ot_pfet_timestamp > $ot_child_timestamp} {
    set ot_child_timestamp $ot_pfet_timestamp
}
cellname timestamp ihp_sg13g2_rom_slice [expr {$ot_child_timestamp + 1}]
save ihp_sg13g2_rom_slice

drc style drc(full)
drc check
drc catchup
puts "OT_DRC_COUNT_BEGIN"
drc count total
puts "OT_DRC_DETAILS=[drc listall why]"
puts "OT_DRC_COUNT_END"

gds write ihp_sg13g2_rom_slice
extract style ngspice()
extract path .
extract all
ext2spice lvs
ext2spice hierarchy off
ext2spice subcircuit on
ext2spice subcircuit top on
ext2spice -o ihp_sg13g2_rom_slice.extracted.spice ihp_sg13g2_rom_slice.ext

# Capacitance-preserving electrical netlist. Detailed resistance remains a
# separately identified extraction gate.
ext2spice cthresh 0
ext2spice -o ihp_sg13g2_rom_slice.pex.spice ihp_sg13g2_rom_slice.ext
quit -noprompt
