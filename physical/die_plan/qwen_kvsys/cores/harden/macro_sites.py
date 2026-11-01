"""Static hard-macro sites with exact OpenDB instance identity resolution."""


def static_placement_tcl(blocks):
    lines = [
        '# GENERATED: explicit core macro plan (same registered RTL and external slot)',
        'set blk [ord::get_db_block]', 'set dbu [$blk getDbUnitsPerMicron]',
        r'proc ot_macro_literal_name {name} {return [string map [list {\[} {[} {\]} {]}] $name]}',
        'set ot_macro_names {}',
        'foreach candidate [$blk getInsts] {',
        '  if {[[$candidate getMaster] getType] ne "BLOCK"} {continue}',
        '  dict lappend ot_macro_names [ot_macro_literal_name [$candidate getName]] $candidate',
        '}',
        'foreach {inst master x y orient} {' + '\n'.join(
            '  {' + b['inst'] + '} ' + b['master'] + f" {b['x']} {b['y']} {b['orient']}"
            for b in blocks) + '\n} {',
        '  set i [$blk findInst $inst]',
        '  if {$i eq {NULL} || $i eq {}} {',
        '    set key [ot_macro_literal_name $inst]',
        '    set hit {}',
        '    if {[dict exists $ot_macro_names $key]} {set hit [dict get $ot_macro_names $key]}',
        '    if {[llength $hit] != 1} {error "planned macro $inst: [llength $hit] literal bracket matches"}',
        '    set i [lindex $hit 0]',
        '  }',
        '  if {[[$i getMaster] getName] ne $master} {error "wrong planned macro master $inst"}',
        '  $i setOrient $orient', '  $i setLocation 0 0', '  set bb [$i getBBox]',
        '  $i setLocation [expr {round($x*$dbu)-[$bb xMin]}] [expr {round($y*$dbu)-[$bb yMin]}]',
        '  $i setPlacementStatus FIRM', '}',
    ]
    return '\n'.join(lines) + '\n'
