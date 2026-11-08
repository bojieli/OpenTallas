"""Default-off parent M7 PG clearance for explicit actual-clock entry windows.

Only actual overlapping parent PG stripe shapes/vias are cut. Native macros,
clock/data nets and every unrelated PG shape remain untouched. Actual parent
PDN connectivity and post-route DRC still qualify the resulting geometry.
"""

def render(cuts):
    out=['# OT_CLOCK_ENTRY_PG_CUT: explicit actual-clock utility access, after pdngen',
         'uplevel #0 {', 'set cep_b [ord::get_db_block]',
         'set cep_u [$cep_b getDbUnitsPerMicron]', 'set cep_done {}',
         'foreach cep_w {']
    for c in cuts:
        if c['layer']!='M7' or len(c['rect_um'])!=4:
            raise ValueError('only explicit M7 utility windows supported')
        out.append('  {'+' '.join(f'{v:.6f}' for v in c['rect_um'])+'}')
    out += ['} {',
        '  lassign $cep_w ax ay bx by',
        '  set X0 [expr {round($ax*$cep_u)}]; set X1 [expr {round($bx*$cep_u)}]',
        '  set Y0 [expr {round($ay*$cep_u)}]; set Y1 [expr {round($by*$cep_u)}]',
        '  foreach net {VDD VSS} {',
        '    set n [$cep_b findNet $net]',
        '    if {$n eq "NULL" || $n eq ""} continue',
        '    lappend cep_done [list $net $X0 $Y0 $X1 $Y1]',
        '    foreach sw [$n getSWires] {',
        '      foreach s [$sw getWires] {',
        '        if {[$s isVia]} continue',
        '        if {[[$s getTechLayer] getName] ne "M7"} continue',
        '        if {[$s xMax] <= $X0 || [$s xMin] >= $X1 || [$s yMax] <= $Y0 || [$s yMin] >= $Y1} continue',
        '        set a [$s xMin]; set b [$s yMin]; set c [$s xMax]; set d [$s yMax]',
        '        if {$d-$b < $c-$a} { error "explicit clock entry encountered nonvertical M7 PG shape" }',
        '        set lay [$s getTechLayer]; set st [$s getWireShapeType]',
        '        odb::dbSBox_destroy $s',
        '        if {$b < $Y0} { odb::dbSBox_create $sw $lay $a $b $c $Y0 $st }',
        '        if {$d > $Y1} { odb::dbSBox_create $sw $lay $a $Y1 $c $d $st }',
        '        lappend cep_done [list $net $a $Y0 $c $Y1]',
        '      }', '    }', '  }', '}',
        'foreach cut $cep_done {', '  lassign $cut net X0 Y0 X1 Y1',
        '  foreach sw [[$cep_b findNet $net] getSWires] {',
        '    foreach s [$sw getWires] {',
        '      if {![$s isVia]} continue',
        '      if {[$s xMax] <= $X0 || [$s xMin] >= $X1 || [$s yMax] <= $Y0 || [$s yMin] >= $Y1} continue',
        '      foreach v [list [$s getTechVia] [$s getBlockVia]] {',
        '        if {$v eq "NULL" || $v eq ""} continue',
        '        if {"M7" in [list [[$v getTopLayer] getName] [[$v getBottomLayer] getName]]} {',
        '          odb::dbSBox_destroy $s; break', '        }', '      }', '    }', '  }', '}',
        'puts "OT_CLOCK_ENTRY_PG_CUT stripe_cuts=[llength $cep_done]"', '}']
    return '\n'.join(out)+'\n'
