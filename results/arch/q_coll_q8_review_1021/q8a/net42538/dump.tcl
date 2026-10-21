# Read-only OpenDB facts from one preserved failed-route checkpoint.
# No Liberty/SDC/STA, mutation, placement, repair, routing or write_db command.
read_db /inputs/checkpoint.odb
set b [ord::get_db_block]
set tech [ord::get_db_tech]
set u [$b getDbUnitsPerMicron]
set name $::env(DUMP_NET)
set net [$b findNet $name]
if {$net in {NULL {}}} {error "requested actual failed net absent: $name"}
puts "META\tnet\t$name\tdbu_per_micron\t$u"
puts "LIMIT\tcheckpoint saved after hook_shapes_dropped; deleted transient hook obstructions cannot be recovered from this ODB"
proc box {o} {list [$o xMin] [$o yMin] [$o xMax] [$o yMax]}
proc overlaps {a c} {
    lassign $a x0 y0 x1 y1; lassign $c a0 b0 a1 b1
    expr {$x0 <= $a1 && $x1 >= $a0 && $y0 <= $b1 && $y1 >= $b0}
}
proc unionbox {a c} {
    if {$a eq ""} {return $c}
    lassign $a x0 y0 x1 y1; lassign $c a0 b0 a1 b1
    list [expr {min($x0,$a0)}] [expr {min($y0,$b0)}] [expr {max($x1,$a1)}] [expr {max($y1,$b1)}]
}
proc point {orient x y} {
    switch -- $orient {
        R0 - N {return [list $x $y]}
        R90 - W {return [list [expr {-$y}] $x]}
        R180 - S {return [list [expr {-$x}] [expr {-$y}]]}
        R270 - E {return [list $y [expr {-$x}]]}
        MX - FS {return [list $x [expr {-$y}]]}
        MY - FN {return [list [expr {-$x}] $y]}
        MXR90 - FW {return [list $y $x]}
        MYR90 - FE {return [list [expr {-$y}] [expr {-$x}]]}
        default {error "unsupported observed orientation $orient"}
    }
}
proc transformbox {orient bb} {
    lassign $bb x0 y0 x1 y1
    set out ""
    foreach p [list [list $x0 $y0] [list $x0 $y1] [list $x1 $y0] [list $x1 $y1]] {
        lassign [point $orient {*}$p] x y
        set out [unionbox $out [list $x $y $x $y]]
    }
    return $out
}
proc shifted {bb dx dy} {
    lassign $bb x0 y0 x1 y1
    list [expr {$x0+$dx}] [expr {$y0+$dy}] [expr {$x1+$dx}] [expr {$y1+$dy}]
}
proc shapes {it} {
    set out {}
    foreach mp [[$it getMTerm] getMPins] {
        foreach g [$mp getGeometry] {
            set layer [$g getTechLayer]
            if {$layer in {NULL {}}} continue
            lappend out [list [$layer getName] [box $g]]
        }
    }
    return $out
}
proc translation {it} {
    set i [$it getInst]; set orient [$i getOrient]
    set local ""
    foreach s [shapes $it] {set local [unionbox $local [transformbox $orient [lindex $s 1]]]}
    if {$local eq ""} {error "actual pin has no local MPin rectangles"}
    set actual [box [$it getBBox]]
    lassign $local x0 y0 x1 y1; lassign $actual a0 b0 a1 b1
    if {$x1-$x0 != $a1-$a0 || $y1-$y0 != $b1-$b0} {error "MPin/actual ITerm bbox dimensions differ"}
    return [list $orient [expr {$a0-$x0}] [expr {$b0-$y0}]]
}
set bb ""
foreach it [$net getITerms] {
    set i [$it getInst];set m [$i getMaster];set pb [box [$it getBBox]]
    set bb [unionbox $bb $pb]
    puts "ITERM\t[$i getName]/[[$it getMTerm] getName]\t[[$it getMTerm] getIoType]\t[$m getName]\t[$i getOrient]\t$pb\tINSTANCE_BBOX\t[box [$i getBBox]]"
    if {[catch {translation $it} tr]} {puts "UNAVAILABLE\tpin transform\t$tr"; continue}
    lassign $tr orient dx dy
    foreach s [shapes $it] {
        lassign $s layer local
        puts "PINSHAPE\t[$i getName]/[[$it getMTerm] getName]\t$layer\t[shifted [transformbox $orient $local] $dx $dy]\tLOCAL\t$local"
    }
}
foreach bt [$net getBTerms] {
    puts "BTERM\t[$bt getName]\t[$bt getIoType]"
    foreach pin [$bt getBPins] {foreach g [$pin getBoxes] {
        set pb [box $g];set bb [unionbox $bb $pb]
        puts "BTERM_SHAPE\t[$bt getName]\t[[$g getTechLayer] getName]\t$pb"
    }}
}
if {$bb eq ""} {error "net has no physical endpoint boxes"}
puts "NET_ENDPOINT_BBOX\t$bb"
lassign $bb x0 y0 x1 y1
set margin [expr {10*$u}]
set region [list [expr {$x0-$margin}] [expr {$y0-$margin}] [expr {$x1+$margin}] [expr {$y1+$margin}]]
puts "NEARBY_REGION\t$region\tmargin_um\t10"
foreach i [$b getInsts] {
    set m [$i getMaster]
    if {![$m isBlock] || ![overlaps $region [box [$i getBBox]]]} continue
    puts "MACRO\t[$i getName]\t[$m getName]\t[$i getOrient]\t[box [$i getBBox]]"
    set tr ""
    foreach it [$i getITerms] {if {![catch {translation $it} candidate]} {set tr $candidate;break}}
    if {$tr eq ""} {puts "UNAVAILABLE\tmacro OBS transform\t[$i getName]";continue}
    lassign $tr orient dx dy
    foreach o [$m getObstructions] {
        set layer [$o getTechLayer]
        if {$layer in {NULL {}}} continue
        set ob [shifted [transformbox $orient [box $o]] $dx $dy]
        if {[overlaps $region $ob]} {puts "MACRO_OBS\t[$i getName]\t[$layer getName]\t$ob"}
    }
}
foreach o [$b getObstructions] {
    set ob [box [$o getBBox]]
    if {[overlaps $region $ob]} {puts "ROUTING_OBSTRUCTION\t[[$o getTechLayer] getName]\t$ob"}
}
foreach o [$b getBlockages] {
    set ob [box [$o getBBox]]
    if {[overlaps $region $ob]} {puts "PLACEMENT_BLOCKAGE\t$ob"}
}
set grid [$b getGCellGrid]
if {$grid in {NULL {}}} {puts "UNAVAILABLE\tstored GCell grid"} else {
    set gx [$grid getGridX];set gy [$grid getGridY]
    puts "GRIDX\t$gx"; puts "GRIDY\t$gy"
    set ix {};set iy {};set k 0
    foreach x $gx {if {$x >= [lindex $region 0] && $x <= [lindex $region 2]} {lappend ix $k};incr k}
    set k 0;foreach y $gy {if {$y >= [lindex $region 1] && $y <= [lindex $region 3]} {lappend iy $k};incr k}
    set cells [expr {[llength $ix]*[llength $iy]}]
    puts "GRID_REGION_CELLS\t$cells"
    if {$cells > 20000} {puts "LIMIT\tgrid local window exceeds20000cells; capacity dump not expanded"} else {
        foreach ln {M1 M2 M3 M4 M5 M6 M7 M8 M9} {
            set layer [$tech findLayer $ln]
            if {$layer in {NULL {}}} continue
            foreach x $ix {foreach y $iy {
                if {[catch {$grid getCapacity $layer $x $y} cap] || [catch {$grid getUsage $layer $x $y} use]} {
                    puts "UNAVAILABLE\tstored GCell capacity/usage\t$ln";break
                }
                puts "GRID\t$ln\t$x\t$y\t$cap\t$use"
            }}
        }
    }
}
puts "READONLY_NET_DUMP COMPLETE $name (no design mutation/STA/route)"
