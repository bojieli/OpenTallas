# Parametric via-programmed NOR mask-ROM bit array, IHP SG13G2 public deck.
#
# Topology, and why it costs what it costs. Each bit is one nMOS whose gate is a
# horizontal poly wordline and whose source shares a horizontal metal1 ground
# rail with the cell in the mirrored row. Its drain is a private diffusion
# island with a private metal1 pad, and the stored bit is the presence or
# absence of one via1 from that pad to the vertical metal2 bitline. The drain
# islands of two adjacent rows are split by a diffusion gap rather than shared,
# which costs height, and that cost is not optional: a shared drain contact
# would give two rows one programming via and the array could then only store
# pairs. Late via personalisation is the point of a mask ROM, so the via is at
# the top of the stack and every bit pays for its own.
#
# All dimensions are in nanometres in the parameter block and converted to
# microns for Magic. Every default below sits on a floor of the installed public
# deck; `tools/run_ihp_bitcell_density.py` proves that by shrinking each one and
# recording the rule that refuses it.
#
# Consumers:
#   tools/run_ihp_bitcell_density.py   bitcell pitch and the ROM/SRAM area ratio
#   tools/run_ihp_rom_read_energy.py   extracted bitline capacitance and read energy
#   tools/run_ihp_rom_macro_route.py   drawn macro footprint for place-and-route
#
# IHP SG13G2 is a 130 nm process. Nothing produced from this file is an N7/N6/
# N5/N4 value and none of it may be feature-size scaled into one.

# ---- parameters (overridable through the OT_* environment) -------------
proc pget {name default} {
    if {[info exists ::env($name)]} { return [expr {double($::env($name))}] }
    return [expr {double($default)}]
}
set NROW    [expr {int([pget OT_NROW 16])}]
set NCOL    [expr {int([pget OT_NCOL 8])}]
set PX      [pget OT_PX  510]      ;# column pitch
set WD      [pget OT_WD  300]      ;# diffusion strip width
set GS      [pget OT_GS  380]      ;# source-region height between poly edges
set DA      [pget OT_DA  340]      ;# per-cell drain island height
set DG      [pget OT_DG  210]      ;# drain-island split gap
set PW      [pget OT_PW  130]      ;# poly wordline width
set CT      [pget OT_CT  160]      ;# contact size
set RAILH   [pget OT_RAILH 260]    ;# metal1 ground rail height
set PADX    [pget OT_PADX 330]     ;# metal1 drain pad width
set V1      [pget OT_V1  200]      ;# via1 size
set BLW     [pget OT_BLW 300]      ;# metal2 bitline width
set PADGAP  [pget OT_PADGAP 180]   ;# metal1 pad-to-pad / pad-to-rail clearance
set TAPGAP  [pget OT_TAPGAP 400]   ;# n-diffusion to p-tap diffusion clearance
set OT_PATTERN [expr {[info exists ::env(OT_PATTERN)] ? $::env(OT_PATTERN) : "prand"}]
set TOPCELL [expr {[info exists ::env(OT_TOPCELL)] ? $::env(OT_TOPCELL) : "ihp_rom_bitarray"}]

set P2 [expr {$GS + 2*$PW + $DA + $DG + $DA}]   ;# height of a two-row period
set PY [expr {$P2 / 2.0}]

proc u {v} { return [expr {$v / 1000.0}] }

# deterministic stored-data pattern
proc ot_bit {row col} {
    switch -- $::OT_PATTERN {
        all1    { return 1 }
        all0    { return 0 }
        checker { return [expr {($row + $col) % 2}] }
        default {
            # deterministic 32-bit xorshift keyed by (row, col); no RNG state
            set x [expr {(($row + 1) * 73856093) ^ (($col + 1) * 19349663) ^ 0x5bd1e995}]
            set x [expr {$x & 0xffffffff}]
            set x [expr {($x ^ ($x << 13)) & 0xffffffff}]
            set x [expr {$x ^ ($x >> 17)}]
            set x [expr {($x ^ ($x << 5)) & 0xffffffff}]
            return [expr {$x & 1}]
        }
    }
}

proc pbox {layer x1 y1 x2 y2} {
    box values [u $x1]um [u $y1]um [u $x2]um [u $y2]um
    paint $layer
}
proc ebox {layer x1 y1 x2 y2} {
    box values [u $x1]um [u $y1]um [u $x2]um [u $y2]um
    erase $layer
}

load $TOPCELL -silent
units microns
snap internal

set NPAIR [expr {int(ceil($NROW / 2.0))}]
set ARRAY_W [expr {$NCOL * $PX}]

# Periodic substrate tap rows. Without them a large array violates the public
# latch-up rule LU.b (n-diffusion must be within 20 um of a p-tap), which a
# bitcell-pitch-only density number silently ignores. TAP_EVERY counts
# two-row periods between tap bands; 0 disables the bands entirely and is only
# legal for arrays small enough that the frame taps already satisfy LU.b.
set TAP_EVERY [expr {int([pget OT_TAP_EVERY 0])}]
set TAPBAND [expr {2*$TAPGAP + 400 + $GS}]
proc ot_pair_y {p} {
    if {$::TAP_EVERY <= 0} { return [expr {$p * $::P2}] }
    return [expr {$p * $::P2 + (int($p / $::TAP_EVERY)) * $::TAPBAND}]
}
set NGROUP [expr {$TAP_EVERY > 0 ? int(ceil(double($NPAIR) / $TAP_EVERY)) : 1}]
# y = 0 is the centre of the bottom shared source region.
set YBOT [expr {-$GS/2.0}]
set YTOP [expr {[ot_pair_y [expr {$NPAIR - 1}]] + $P2 + $GS/2.0}]
set ARRAY_H [expr {$YTOP - $YBOT}]

# ---- diffusion strips, transistors, contacts ---------------------------
for {set c 0} {$c < $NCOL} {incr c} {
    set xc [expr {$c * $PX + $PX/2.0}]
    set x1 [expr {$xc - $WD/2.0}]
    set x2 [expr {$xc + $WD/2.0}]
    # one n-diffusion strip per tap-separated group, split at the drain gaps
    for {set g 0} {$g < $NGROUP} {incr g} {
        set pf [expr {$TAP_EVERY > 0 ? $g * $TAP_EVERY : 0}]
        set pl [expr {$TAP_EVERY > 0 ? min(($g+1)*$TAP_EVERY, $NPAIR) - 1 : $NPAIR - 1}]
        pbox ndiff $x1 [expr {[ot_pair_y $pf] - $GS/2.0}] \
            $x2 [expr {[ot_pair_y $pl] + $P2 + $GS/2.0}]
    }
    for {set p 0} {$p < $NPAIR} {incr p} {
        set y0 [ot_pair_y $p]
        set ga [expr {$y0 + $GS/2.0 + $PW + $DA}]
        ebox ndiff $x1 $ga $x2 [expr {$ga + $DG}]
    }
}

# poly wordlines: continuous rows crossing every diffusion strip
set WLSTRAP [expr {[info exists ::env(OT_WL_STRAP)] ? 1 : 0}]
set PADSZ 500
set PADX_EVEN -900
set PADX_ODD -1700
set XPOLY1 [expr {$WLSTRAP ? -2000 : -$PW - 400}]
set XPOLY2 [expr {$ARRAY_W + $PW + 400}]
for {set p 0} {$p < $NPAIR} {incr p} {
    set y0 [ot_pair_y $p]
    set wl0 [expr {$y0 + $GS/2.0}]
    set wl1 [expr {$y0 + $GS/2.0 + $PW + $DA + $DG + $DA}]
    pbox poly $XPOLY1 $wl0 $XPOLY2 [expr {$wl0 + $PW}]
    if {2*$p + 1 < $NROW} {
        pbox poly $XPOLY1 $wl1 $XPOLY2 [expr {$wl1 + $PW}]
    }
}

# source contacts and horizontal metal1 ground rails
set RAIL_Y {}
for {set p 0} {$p <= $NPAIR} {incr p} {
    if {$p == $NPAIR} {
        set ys [expr {[ot_pair_y [expr {$NPAIR - 1}]] + $P2}]
    } elseif {$TAP_EVERY > 0 && $p > 0 && $p % $TAP_EVERY == 0} {
        # a group boundary carries two source rows: the top of the group below
        # and the bottom of the group above
        set ys [expr {[ot_pair_y [expr {$p - 1}]] + $P2}]
        lappend RAIL_Y $ys
        pbox metal1 -200 [expr {$ys - $RAILH/2.0}] \
            [expr {$ARRAY_W + $RAILH/2.0}] [expr {$ys + $RAILH/2.0}]
        for {set c 0} {$c < $NCOL} {incr c} {
            set xc [expr {$c * $PX + $PX/2.0}]
            pbox ndiffc [expr {$xc - $CT/2.0}] [expr {$ys - $CT/2.0}] \
                [expr {$xc + $CT/2.0}] [expr {$ys + $CT/2.0}]
        }
        set ys [ot_pair_y $p]
    } else {
        set ys [ot_pair_y $p]
    }
    lappend RAIL_Y $ys
    pbox metal1 -200 [expr {$ys - $RAILH/2.0}] \
        [expr {$ARRAY_W + $RAILH/2.0}] [expr {$ys + $RAILH/2.0}]
    for {set c 0} {$c < $NCOL} {incr c} {
        set xc [expr {$c * $PX + $PX/2.0}]
        pbox ndiffc [expr {$xc - $CT/2.0}] [expr {$ys - $CT/2.0}] \
            [expr {$xc + $CT/2.0}] [expr {$ys + $CT/2.0}]
    }
}

# drain islands: contact, metal1 pad, programming via1
set PROG {}
for {set c 0} {$c < $NCOL} {incr c} {
    set xc [expr {$c * $PX + $PX/2.0}]
    for {set p 0} {$p < $NPAIR} {incr p} {
        set y0 [ot_pair_y $p]
        set aB [expr {$y0 + $GS/2.0 + $PW}]
        set aT [expr {$aB + $DA}]
        set bB [expr {$aT + $DG}]
        set bT [expr {$bB + $DA}]
        # row 2p uses island A, row 2p+1 uses island B
        foreach {row cy cbot ctop} [list \
            [expr {2*$p}]   [expr {$aB + 110 + $CT/2.0}] $aB $aT \
            [expr {2*$p+1}] [expr {$bT - 110 - $CT/2.0}] $bB $bT] {
            if {$row >= $NROW} { continue }
            pbox ndiffc [expr {$xc - $CT/2.0}] [expr {$cy - $CT/2.0}] \
                [expr {$xc + $CT/2.0}] [expr {$cy + $CT/2.0}]
            # metal1 pad, clamped away from the ground rails and each other
            set prail [expr {$y0 + $RAILH/2.0 + $PADGAP}]
            set nrail [expr {$y0 + $P2 - $RAILH/2.0 - $PADGAP}]
            set mid   [expr {$aT + $DG/2.0}]
            if {$row % 2 == 0} {
                set py1 $prail
                set py2 [expr {$mid - $PADGAP/2.0}]
            } else {
                set py1 [expr {$mid + $PADGAP/2.0}]
                set py2 $nrail
            }
            pbox metal1 [expr {$xc - $PADX/2.0}] $py1 [expr {$xc + $PADX/2.0}] $py2
            # programming via1 present for a stored one, absent for a zero
            set bit [ot_bit $row $c]
            if {$bit} {
                set vy [expr {($py1 + $py2)/2.0}]
                pbox via1 [expr {$xc - $V1/2.0}] [expr {$vy - $V1/2.0}] \
                    [expr {$xc + $V1/2.0}] [expr {$vy + $V1/2.0}]
                lappend PROG [list $c $row]
            }
        }
    }
}

# metal2 bitlines, and (when a routable macro is wanted) a staggered Metal3
# escape pad per column.  A bitline pin cannot simply be the top of the M2
# trunk: the trunk is 0.30 um wide on a 0.51 um pitch and the router's vertical
# track pitch is 0.48 um, so a trunk-top pin is not guaranteed to contain a
# track and detailed routing refuses it.  Escaping to Metal3 in two staggered
# rows makes every bitline reachable.  That escape region is real periphery
# area and it is inside the measured macro footprint.
set BLTOP [expr {$WLSTRAP ? $YTOP + 1900 : $YTOP + 300}]
set M3PAD_W 600
set M3PAD_H 500
for {set c 0} {$c < $NCOL} {incr c} {
    set xc [expr {$c * $PX + $PX/2.0}]
    pbox metal2 [expr {$xc - $BLW/2.0}] [expr {$YBOT - 300}] \
        [expr {$xc + $BLW/2.0}] $BLTOP
    if {$WLSTRAP} {
        set pady [expr {$c % 2 == 0 ? $YTOP + 550 : $YTOP + 1350}]
        pbox metal3 [expr {$xc - $M3PAD_W/2.0}] [expr {$pady - $M3PAD_H/2.0}] \
            [expr {$xc + $M3PAD_W/2.0}] [expr {$pady + $M3PAD_H/2.0}]
        pbox via2 [expr {$xc - 100}] [expr {$pady - 100}] \
            [expr {$xc + 100}] [expr {$pady + 100}]
    }
}

# ---- periodic substrate tap bands ---------------------------------------
if {$TAP_EVERY > 0} {
    for {set g 1} {$g < $NGROUP} {incr g} {
        set below [expr {[ot_pair_y [expr {$g*$TAP_EVERY - 1}]] + $P2 + $GS/2.0}]
        set band1 [expr {$below + $TAPGAP}]
        set band2 [expr {$band1 + 400}]
        set bl [expr {$XPOLY1 - $TAPGAP - 400}]
        set br [expr {$XPOLY2 + $TAPGAP + 400}]
        pbox psubdiff $bl $band1 $br $band2
        pbox metal1 $bl $band1 $br $band2
        set yc [expr {($band1 + $band2)/2.0}]
        for {set x [expr {$bl + 650}]} {$x <= [expr {$br - 650}]} {set x [expr {$x + 500}]} {
            pbox psubdiffcont [expr {$x - $CT/2.0}] [expr {$yc - $CT/2.0}] \
                [expr {$x + $CT/2.0}] [expr {$yc + $CT/2.0}]
        }
    }
}

# ---- wordline strap ------------------------------------------------------
if {$WLSTRAP} {
    for {set j 0} {$j < $NROW} {incr j} {
        set p [expr {$j / 2}]
        set y0 [ot_pair_y $p]
        if {$j % 2 == 0} {
            set wl [expr {$y0 + $GS/2.0}]
            set px $PADX_EVEN
        } else {
            set wl [expr {$y0 + $GS/2.0 + $PW + $DA + $DG + $DA}]
            set px $PADX_ODD
        }
        set yc [expr {$wl + $PW/2.0}]
        pbox poly [expr {$px - $PADSZ/2.0}] [expr {$yc - $PADSZ/2.0}] \
            [expr {$px + $PADSZ/2.0}] [expr {$yc + $PADSZ/2.0}]
        pbox polycont [expr {$px - $CT/2.0}] [expr {$yc - $CT/2.0}] \
            [expr {$px + $CT/2.0}] [expr {$yc + $CT/2.0}]
        pbox metal1 [expr {$px - $PADSZ/2.0}] [expr {$yc - $PADSZ/2.0}] \
            [expr {$px + $PADSZ/2.0}] [expr {$yc + $PADSZ/2.0}]
        # Metal1 is reserved for the standard cells, so the wordline pin has to
        # be presented on Metal2 for the router to reach it.
        pbox metal2 [expr {$px - $PADSZ/2.0}] [expr {$yc - $PADSZ/2.0}] \
            [expr {$px + $PADSZ/2.0}] [expr {$yc + $PADSZ/2.0}]
        pbox via1 [expr {$px - 100}] [expr {$yc - 100}] \
            [expr {$px + 100}] [expr {$yc + 100}]
    }
    # the even-row poly only has to reach its own pad column
    for {set j 0} {$j < $NROW} {incr j 2} {
        set p [expr {$j / 2}]
        set y0 [ot_pair_y $p]
        set wl [expr {$y0 + $GS/2.0}]
        ebox poly $XPOLY1 $wl [expr {$PADX_EVEN - $PADSZ/2.0}] [expr {$wl + $PW}]
    }
}

# ---- substrate tap frame ------------------------------------------------
set TW 400
set tb [expr {$YBOT - $TAPGAP - $TW}]
set tt [expr {($WLSTRAP ? $YTOP + 2200 : $YTOP) + $TAPGAP + $TW}]
set tl [expr {$XPOLY1 - $TAPGAP - $TW}]
set tr [expr {$XPOLY2 + $TAPGAP + $TW}]
foreach {rx1 ry1 rx2 ry2} [list \
    $tl $tb $tr [expr {$tb + $TW}] \
    $tl [expr {$tt - $TW}] $tr $tt \
    $tl $tb [expr {$tl + $TW}] $tt \
    [expr {$tr - $TW}] $tb $tr $tt] {
    pbox psubdiff $rx1 $ry1 $rx2 $ry2
    pbox metal1 $rx1 $ry1 $rx2 $ry2
}
# tap contacts, inset by the contact enclosure and stepped at a legal pitch
proc tap_run {x1 y1 x2 y2 ct} {
    set m [expr {70 + $ct/2.0}]
    if {($x2 - $x1) >= ($y2 - $y1)} {
        set yc [expr {($y1 + $y2)/2.0}]
        for {set x [expr {$x1 + $m}]} {$x <= [expr {$x2 - $m}]} {set x [expr {$x + 500}]} {
            pbox psubdiffcont [expr {$x - $ct/2.0}] [expr {$yc - $ct/2.0}] \
                [expr {$x + $ct/2.0}] [expr {$yc + $ct/2.0}]
        }
    } else {
        set xc [expr {($x1 + $x2)/2.0}]
        for {set y [expr {$y1 + $m}]} {$y <= [expr {$y2 - $m}]} {set y [expr {$y + 500}]} {
            pbox psubdiffcont [expr {$xc - $ct/2.0}] [expr {$y - $ct/2.0}] \
                [expr {$xc + $ct/2.0}] [expr {$y + $ct/2.0}]
        }
    }
}
tap_run $tl $tb $tr [expr {$tb + $TW}] $CT
tap_run $tl [expr {$tt - $TW}] $tr $tt $CT
tap_run $tl [expr {$tb + $TW + 500}] [expr {$tl + $TW}] [expr {$tt - $TW - 500}] $CT
tap_run [expr {$tr - $TW}] [expr {$tb + $TW + 500}] $tr [expr {$tt - $TW - 500}] $CT

# join the array ground rails to the substrate tap frame
foreach ys $RAIL_Y {
    pbox metal1 -200 [expr {$ys - $RAILH/2.0}] \
        [expr {$tr - $TW}] [expr {$ys + $RAILH/2.0}]
}

# ---- ports -------------------------------------------------------------
proc ot_port {name idx layer x1 y1 x2 y2} {
    box values [expr {$x1/1000.0}]um [expr {$y1/1000.0}]um \
                [expr {$x2/1000.0}]um [expr {$y2/1000.0}]um
    label $name center $layer
    port make $idx
}
set pidx 1
ot_port VSS $pidx metal1 [expr {$tl + $TW + 60}] -60 \
    [expr {$tl + $TW + 260}] 60
for {set j 0} {$j < $NROW} {incr j} {
    set p [expr {$j / 2}]
    set y0 [ot_pair_y $p]
    if {$j % 2 == 0} {
        set wl [expr {$y0 + $GS/2.0}]
    } else {
        set wl [expr {$y0 + $GS/2.0 + $PW + $DA + $DG + $DA}]
    }
    incr pidx
    if {$WLSTRAP} {
        set px [expr {$j % 2 == 0 ? $PADX_EVEN : $PADX_ODD}]
        set yc [expr {$wl + $PW/2.0}]
        ot_port WL$j $pidx metal2 [expr {$px - $PADSZ/2.0}] [expr {$yc - $PADSZ/2.0}] \
            [expr {$px + $PADSZ/2.0}] [expr {$yc + $PADSZ/2.0}]
    } else {
        ot_port WL$j $pidx poly [expr {$XPOLY1 + 40}] [expr {$wl + 20}] \
            [expr {$XPOLY1 + 340}] [expr {$wl + $PW - 20}]
    }
}
for {set c 0} {$c < $NCOL} {incr c} {
    set xc [expr {$c * $PX + $PX/2.0}]
    incr pidx
    if {$WLSTRAP} {
        set pady [expr {$c % 2 == 0 ? $YTOP + 550 : $YTOP + 1350}]
        ot_port BL$c $pidx metal3 [expr {$xc - 280}] [expr {$pady - 230}] \
            [expr {$xc + 280}] [expr {$pady + 230}]
    } else {
        ot_port BL$c $pidx metal2 [expr {$xc - $BLW/2.0 + 20}] [expr {$YTOP + 40}] \
            [expr {$xc + $BLW/2.0 - 20}] [expr {$YTOP + 260}]
    }
}

save $TOPCELL

puts "OT_PARAM|PX|$PX"
puts "OT_PARAM|PY|$PY"
puts "OT_PARAM|P2|$P2"
puts "OT_PARAM|NROW|$NROW"
puts "OT_PARAM|NCOL|$NCOL"
puts "OT_PARAM|CELL_AREA_NM2|[expr {$PX * $PY}]"
puts "OT_PARAM|PROGRAMMED_VIA1|[llength $PROG]"
puts "OT_PARAM|PATTERN|$OT_PATTERN"
puts "OT_PARAM|V1|$V1"
puts "OT_PARAM|TAP_EVERY|$TAP_EVERY"
set fh [open programmed_bits.txt w]
foreach e $PROG { puts $fh "[lindex $e 0] [lindex $e 1]" }
close $fh

select top cell
box
if {![info exists ::env(OT_SKIP_DRC)]} {
select top cell
box
drc style drc(full)
drc check
drc catchup
puts "OT_DRC_TOTAL=[drc list count total]"
select top cell
set L [drc listall why]
for {set i 0} {$i < [llength $L]} {incr i 2} {
    puts "OT_DRC_RULE|[llength [lindex $L [expr {$i+1}]]]|[lindex $L $i]"
    foreach r [lrange [lindex $L [expr {$i+1}]] 0 5] { puts "OT_DRC_AT|$r" }
}
} else {
    # Deliberately does NOT print OT_DRC_TOTAL. A skipped check must never be
    # parseable as a clean check; the runner refuses a result without a total.
    puts "OT_DRC_SKIPPED=1"
}

if {[info exists ::env(OT_LEF)]} {
    lef write $TOPCELL -hide
    puts "OT_LEF_WRITTEN=1"
}

if {[info exists ::env(OT_EXTRACT)]} {
    gds write $TOPCELL
    extract style ngspice()
    extract path .
    extract all
    ext2spice lvs
    ext2spice hierarchy off
    ext2spice subcircuit on
    ext2spice subcircuit top on
    ext2spice -o $TOPCELL.extracted.spice $TOPCELL.ext
    ext2spice cthresh 0
    ext2spice -o $TOPCELL.pex.spice $TOPCELL.ext
}
quit -noprompt
