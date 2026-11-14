"""Exact placement for declared, actually driven native CS stage banks."""
import fnmatch
import hashlib
from soft_reg_banks import validated_banks
from core_station_inventory import native_banks


def prepare(t, txt, source_sha=None, native_manifest=None, wrapper_sources=None):
    rows = validated_banks(t)
    if not rows and native_manifest is None:
        return [], set()
    from native_source_banks import prepare as prepare_sources
    sources, rows = prepare_sources(rows, txt, native_manifest, wrapper_sources or {}, source_sha)
    actual = native_banks(txt)
    sha = source_sha or hashlib.sha256(txt.encode()).hexdigest()
    used = set()
    out = list(sources)
    for row in rows:
        matches = [b for b in actual if any(fnmatch.fnmatchcase(r['name'], row['cell_glob']) for r in b['registers'])]
        if len(matches) != 1:
            raise ValueError('soft CS bank glob must select exactly one actual class/stage: '+row['id'])
        bank = matches[0]
        if not all(fnmatch.fnmatchcase(r['name'], row['cell_glob']) for r in bank['registers']):
            raise ValueError('soft CS bank glob omits actual registers: '+row['id'])
        if bank['id'] in used:
            raise ValueError('soft CS bank actual stage selected twice: '+bank['id'])
        used.add(bank['id'])
        if row['source'] != 'nativeRTL:'+sha+'#'+bank['id']:
            raise ValueError('soft CS bank stale source: '+row['id'])
        if len(row['bit_sites_um']) != bank['flops']:
            raise ValueError('soft CS bank allocation count differs from actual flops: '+row['id'])
        out.append(row)
    return out, {r['cell_glob'] for r in out}


def emit(rows):
    if not rows:
        return []
    specs=[]
    for row in rows:
        if any(c in row['cell_glob']+row['id'] for c in '{}\\\n'):
            raise ValueError('unsafe soft CS bank identifier')
        sites=' '.join('{%g %g}'%tuple(p) for p in row['bit_sites_um'])
        scalars = row.get('native_scalars', [])
        if any(any(c in scalar for c in '{}\n') for scalar in scalars):
            raise ValueError('unsafe native scalar identifier')
        selectors = ' '.join('{'+scalar.replace('\\', '')+'}' for scalar in scalars)
        if scalars:
            specs.append('{{%s} {%s} {%s} %g %g {%s}}'%(row['id'],row['cell_glob'],sites,*row['bit_site_cell_um'],selectors))
        else:
            specs.append('{{%s} {%s} {%s} %g %g}'%(row['id'],row['cell_glob'],sites,*row['bit_site_cell_um']))
    body = TCL if any(r.get('native_scalars') for r in rows) else LEGACY_TCL
    return [body, 'is_soft_cs_banks {'+' '.join(specs)+'}']


TCL=r'''
# Preflight every declared CS bank before moving any of its mapped flops.
proc is_soft_cs_banks {banks} {
  global ff_blk ff_dbu ff_orient ff_sw ff_x0 ff_y0 ff_x1 ff_y1 ff_explicit_occ ff_rh is_n is_fh
  set moves {}; set owned {}; set boxes {}; set hard {}
  foreach inst [$ff_blk getInsts] {
    if {[[$inst getMaster] isBlock]} {
      set bb [$inst getBBox]
      lappend hard [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    }
  }
  set bynet {}
  set need_native 0
  foreach bank $banks {if {[llength [lindex $bank 5]]} {set need_native 1}}
  if {$need_native} {
    foreach net [$ff_blk getNets] {
      set nn [string map {\\ {} . /} [$net getName]]
      set parts [split $nn /]
      for {set j 0} {$j<[llength $parts]} {incr j} {
        dict lappend bynet [join [lrange $parts $j end] /] $net
      }
    }
  }
  foreach bank $banks {
    lassign $bank id pat sites fw fh scalars
    set names {}; set insts {}; set adjuncts {}
    if {[llength $scalars]} {
      # Resolve exact scalar Q-net identity, including hierarchy prefix, before
      # placement. A count or cell-name order cannot identify split array bits.
      foreach scalar $scalars {
        set key [string map {\\ {} . /} $scalar]
        set candidates {}
        if {[dict exists $bynet $key]} {set candidates [lsort -unique [dict get $bynet $key]]}
        if {[llength $candidates]!=1} {error "native source $id scalar net missing/ambiguous: $scalar"}
        set net [lindex $candidates 0]; set chain {}; set visited {}
        while {1} {
          set netname [$net getName]
          if {[dict exists $visited $netname]} {error "native source scalar driver cycle: $scalar"}
          dict set visited $netname 1
          set drivers {}
          foreach term [$net getITerms] {
            if {[$term getIoType] eq "OUTPUT"} {lappend drivers $term}
          }
          if {[llength $drivers]!=1} {error "native source $id scalar lacks one Q driver: $scalar"}
          set term [lindex $drivers 0]; set i [$term getInst]
          set mastername [[$i getMaster] getName]
          if {[string match *DFF* $mastername]} break
          if {(![string match INV* $mastername] && ![string match BUF* $mastername]) || [llength $chain]>=4} {
            error "native source $id scalar is not mapped DFF Q/unary alias: $scalar"
          }
          set inputs {}; set outputs 0
          foreach pin [$i getITerms] {
            if {[$pin getSigType] in {POWER GROUND}} continue
            if {[$pin getIoType] eq "INPUT"} {lappend inputs $pin}
            if {[$pin getIoType] eq "OUTPUT"} {incr outputs}
          }
          if {[llength $inputs]!=1 || $outputs!=1} {error "native source scalar non-unary alias: $scalar"}
          lappend chain $i
          set net [[lindex $inputs 0] getNet]
          if {$net eq "NULL" || $net eq ""} {error "native source scalar floating alias: $scalar"}
        }
        foreach member [concat [list $i] $chain] {
          set nm [string map {\\ {}} [$member getName]]
          if {[dict exists $owned $nm]} {error "native source scalar Q driver reused/merged: $scalar $nm"}
          dict set owned $nm 1
        }
        dict set adjuncts $scalar [lreverse $chain]
        dict set insts $scalar $i; lappend names $scalar
      }
    } else {
      foreach i [$ff_blk getInsts] {
        set nm [string map {\\ {}} [$i getName]]
        if {![string match $pat $nm] || ![string match *DFF* [[$i getMaster] getName]]} continue
        if {[dict exists $owned $nm]} {error "soft CS bank duplicate mapped flop: $nm"}
        dict set owned $nm 1
        dict set insts $nm $i; lappend names $nm
      }
      set names [lsort -dictionary $names]
    }
    if {[llength $names] != [llength $sites]} {error "soft CS bank $id actual mapped count [llength $names] != allocation [llength $sites]"}
    foreach nm $names site $sites {
      set i [dict get $insts $nm]; set m [$i getMaster]
      lassign $site x y
      set cx [expr {round($x*$ff_dbu)}]; set cy [expr {round($y*$ff_dbu)}]
      set members [list $i]
      if {[dict exists $adjuncts $nm]} {set members [concat $members [dict get $adjuncts $nm]]}
      set w 0; set h 0
      foreach member $members {
        set mm [$member getMaster]
        incr w [$mm getWidth]
        set h [expr {max($h,[$mm getHeight])}]
      }
      if {$w>$fw*$ff_dbu+1 || $h>$fh*$ff_dbu+1} {error "soft CS bank $id mapped master exceeds footprint: $nm"}
      if {![dict exists $ff_orient $cy] || ($cx-$ff_x0)%$ff_sw!=0} {error "soft CS bank $id off row/site: $x $y"}
      if {$cx<$ff_x0 || $cy<$ff_y0 || $cx+$w>$ff_x1 || $cy+$h>$ff_y1} {error "soft CS bank $id outside core"}
      if {[ff_hits_explicit $cx $cy $w $h]} {error "soft CS bank $id overlaps reserved footprint"}
      foreach box $hard {
        lassign $box a b c d
        if {$cx<$c && $a<$cx+$w && $cy<$d && $b<$cy+$h} {error "soft CS bank $id overlaps hard core"}
      }
      set r0 [expr {int(floor(double($cy-$ff_y0)/$ff_rh))}]
      for {set row $r0} {$ff_y0+$row*$ff_rh<$cy+$h} {incr row} {
        if {[dict exists $boxes $row]} {
          foreach box [dict get $boxes $row] {
            lassign $box a b c d
            if {$cx<$c && $a<$cx+$w && $cy<$d && $b<$cy+$h} {error "soft CS bank $id overlaps another allocation"}
          }
        }
        dict lappend boxes $row [list $cx $cy [expr {$cx+$w}] [expr {$cy+$h}]]
      }
      set mx $cx
      foreach member $members {
        set mm [$member getMaster]
        set mw [$mm getWidth]; set mh [$mm getHeight]
        lappend moves [list $member [$member getName] $mx $cy $mw $mh $id]
        incr mx $mw
      }
    }
  }
  foreach move $moves {
    lassign $move i nm cx cy w h id
    $i setPlacementStatus PLACED; $i setOrient [dict get $ff_orient $cy]
    $i setLocation $cx $cy; $i setPlacementStatus FIRM
    for {set row [expr {int(floor(double($cy-$ff_y0)/$ff_rh))}]} {$ff_y0+$row*$ff_rh<$cy+$h} {incr row} {
      dict lappend ff_explicit_occ $row [list $cx $cy [expr {$cx+$w}] [expr {$cy+$h}]]
    }
    puts $is_fh "$nm\tsoftcs:$id\t[expr {$cx/double($ff_dbu)}]\t[expr {$cy/double($ff_dbu)}]\t-"
    incr is_n
  }
  puts "OT_SOFT_CS_BANKS: [llength $banks] banks [llength $moves] mapped cells FIRM"
}
'''


def preserve_drivers(txt, rows):
    """Keep only the selected, actually driven registers through synthesis.

    The post-synthesis Tcl count guard remains mandatory; keep is no substitute
    for checking that each declared scalar FF was physically realized.
    """
    import re
    from core_station_inventory import REG
    globs=[r['cell_glob'] for r in rows if not r.get('native_scalars')]
    def add(match):
        if any(fnmatch.fnmatchcase(match.group(3),g) for g in globs):
            return '(* keep = 1 *) '+match.group(0)
        return match.group(0)
    return REG.sub(add,txt)

# Preserve legacy generated kits byte for byte unless native source banks opt in.
LEGACY_TCL = r'''
# Preflight every declared CS bank before moving any of its mapped flops.
proc is_soft_cs_banks {banks} {
  global ff_blk ff_dbu ff_orient ff_sw ff_x0 ff_y0 ff_x1 ff_y1 ff_explicit_occ ff_rh is_n is_fh
  set moves {}; set owned {}; set boxes {}; set hard {}
  foreach inst [$ff_blk getInsts] {
    if {[[$inst getMaster] isBlock]} {
      set bb [$inst getBBox]
      lappend hard [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    }
  }
  foreach bank $banks {
    lassign $bank id pat sites fw fh
    set names {}; set insts {}
    foreach i [$ff_blk getInsts] {
      set nm [string map {\\ {}} [$i getName]]
      if {![string match $pat $nm] || ![string match *DFF* [[$i getMaster] getName]]} continue
      if {[dict exists $owned $nm]} {error "soft CS bank duplicate mapped flop: $nm"}
      dict set owned $nm 1
      dict set insts $nm $i; lappend names $nm
    }
    set names [lsort -dictionary $names]
    if {[llength $names] != [llength $sites]} {error "soft CS bank $id actual mapped count [llength $names] != allocation [llength $sites]"}
    foreach nm $names site $sites {
      set i [dict get $insts $nm]; set m [$i getMaster]
      lassign $site x y
      set cx [expr {round($x*$ff_dbu)}]; set cy [expr {round($y*$ff_dbu)}]
      set w [$m getWidth]; set h [$m getHeight]
      if {$w>$fw*$ff_dbu+1 || $h>$fh*$ff_dbu+1} {error "soft CS bank $id mapped master exceeds footprint: $nm"}
      if {![dict exists $ff_orient $cy] || ($cx-$ff_x0)%$ff_sw!=0} {error "soft CS bank $id off row/site: $x $y"}
      if {$cx<$ff_x0 || $cy<$ff_y0 || $cx+$w>$ff_x1 || $cy+$h>$ff_y1} {error "soft CS bank $id outside core"}
      if {[ff_hits_explicit $cx $cy $w $h]} {error "soft CS bank $id overlaps reserved footprint"}
      foreach box $hard {
        lassign $box a b c d
        if {$cx<$c && $a<$cx+$w && $cy<$d && $b<$cy+$h} {error "soft CS bank $id overlaps hard core"}
      }
      set r0 [expr {int(floor(double($cy-$ff_y0)/$ff_rh))}]
      for {set row $r0} {$ff_y0+$row*$ff_rh<$cy+$h} {incr row} {
        if {[dict exists $boxes $row]} {
          foreach box [dict get $boxes $row] {
            lassign $box a b c d
            if {$cx<$c && $a<$cx+$w && $cy<$d && $b<$cy+$h} {error "soft CS bank $id overlaps another allocation"}
          }
        }
        dict lappend boxes $row [list $cx $cy [expr {$cx+$w}] [expr {$cy+$h}]]
      }
      lappend moves [list $i $nm $cx $cy $w $h $id]
    }
  }
  foreach move $moves {
    lassign $move i nm cx cy w h id
    $i setPlacementStatus PLACED; $i setOrient [dict get $ff_orient $cy]
    $i setLocation $cx $cy; $i setPlacementStatus FIRM
    for {set row [expr {int(floor(double($cy-$ff_y0)/$ff_rh))}]} {$ff_y0+$row*$ff_rh<$cy+$h} {incr row} {
      dict lappend ff_explicit_occ $row [list $cx $cy [expr {$cx+$w}] [expr {$cy+$h}]]
    }
    puts $is_fh "$nm\tsoftcs:$id\t[expr {$cx/double($ff_dbu)}]\t[expr {$cy/double($ff_dbu)}]\t-"
    incr is_n
  }
  puts "OT_SOFT_CS_BANKS: [llength $banks] banks [llength $moves] actual flops FIRM"
}
'''
