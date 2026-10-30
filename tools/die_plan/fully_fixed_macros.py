"""Opt-in validation-only macro placement for fully fixed parent-plan macros.

Installed through ORFS PRE_MACRO_PLACE_TCL. The ordinary macro placement deck
runs next; the process-local rtl_macro_placer entry then validates its result.
Normal POST/report/database writing, tapcell, PDN and placement stages remain.
"""
import json
import re
from pathlib import Path


VALIDATOR = r'''
proc ot_fixed_macro_validate {} {
  set b [ord::get_db_block]
  set dbu [$b getDbUnitsPerMicron]
  set actual {}
  foreach i [$b getInsts] {
    if {[[$i getMaster] isBlock]} {dict set actual [$i getName] $i}
  }
  if {[lsort [dict keys $actual]] ne [lsort [dict keys $::ot_fixed_macro_expected]]} {
    error "OT_FIXED_MACROS actual block inventory differs from the complete parent plan"
  }
  set core [$b getCoreArea]
  set core_box [list [$core xMin] [$core yMin] [$core xMax] [$core yMax]]
  set wanted_core [lmap x $::ot_fixed_macro_core_um {expr {round($x*$dbu)}}]
  if {$core_box ne $wanted_core} {error "OT_FIXED_MACROS core differs from the parent plan"}
  set boxes {}
  dict for {name spec} $::ot_fixed_macro_expected {
    lassign $spec master x y w h orient
    set i [dict get $actual $name];set m [$i getMaster]
    if {[$m getName] ne $master || [$i getPlacementStatus] ne "LOCKED"} {
      error "OT_FIXED_MACROS $name requires the exact planned master and LOCKED status"
    }
    if {[$m getWidth] != round($w*$dbu) || [$m getHeight] != round($h*$dbu) || [$i getOrient] ne $orient} {
      error "OT_FIXED_MACROS $name master dimensions/orientation differ from the parent plan"
    }
    set bb [$i getBBox]
    set box [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    set wanted [list [expr {round($x*$dbu)}] [expr {round($y*$dbu)}] [expr {round(($x+$w)*$dbu)}] [expr {round(($y+$h)*$dbu)}]]
    if {$box ne $wanted} {error "OT_FIXED_MACROS $name moved from its exact parent-plan rectangle"}
    lassign $box ax ay bx by
    lassign $core_box cx cy dx dy
    if {$ax<$cx || $ay<$cy || $bx>$dx || $by>$dy} {error "OT_FIXED_MACROS $name lies outside the core"}
    dict for {other other_box} $boxes {
      lassign $other_box ox oy px py
      if {min($bx,$px)>max($ax,$ox) && min($by,$py)>max($ay,$oy)} {
        error "OT_FIXED_MACROS $name overlaps $other"
      }
    }
    dict set boxes $name $box
  }
  puts "OT_FIXED_MACROS PASS [dict size $actual] exact LOCKED parent-plan macros; optimization unnecessary"
}
if {[llength [info commands ::ot_fixed_macro_original]] || ![llength [info commands ::rtl_macro_placer]]} {
  error "OT_FIXED_MACROS requires one native macro placer before installing the scoped hook"
}
rename ::rtl_macro_placer ::ot_fixed_macro_original
proc ::rtl_macro_placer {args} {ot_fixed_macro_validate}
'''


def install(t,kd,macros,core_area,root):
    """Return config lines; absent/false leaves all default kit files unchanged."""
    enabled=t.get('fully_fixed_macros',False)
    if not isinstance(enabled,bool):raise ValueError('fully_fixed_macros must be boolean')
    if not enabled:return []
    if not macros:raise ValueError('fully_fixed_macros requires a nonempty complete macro inventory')
    expected=[];seen=set()
    declared={}
    for c in t.get('hard_cores',[])+t.get('contents',[]):
        if c.get('lef'):
            name=c.get('physical_inst',c['inst'])
            name=re.sub(r'(?<!\\)([\[\]])',r'\\\1',name)
            declared.setdefault(name,c.get('outline_um'))
    for inst,master,lef,lib,x,y,orient in macros:
        if any(c in inst+master for c in '{}\n\r;'):raise ValueError('unsupported macro identity in fully fixed contract')
        inst=re.sub(r'(?<!\\)([\[\]])',r'\\\1',inst)
        if inst in seen:raise ValueError('duplicate fully fixed macro instance '+inst)
        seen.add(inst)
        text=(Path(root)/lef).read_text()
        found=re.search(r'\bMACRO\s+'+re.escape(master)+r'\s+(.*?)\bEND\s+'+re.escape(master)+r'\b',text,re.S)
        size=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',found[1]) if found else None
        if size is None:raise ValueError('fully fixed macro lacks exact LEF master size '+master)
        w,h=map(float,size.groups())
        outline=declared.get(inst)
        if not outline or len(outline)!=2 or any(abs(a-b)>1e-6 for a,b in zip(outline,(w,h))):
            raise ValueError('fully fixed LEF size differs from declared parent-plan outline '+inst)
        if orient not in ('R0','MX','MY','R180'):raise ValueError('unsupported fully fixed macro orientation '+orient)
        expected.append(dict(instance=inst,master=master,origin_um=[round(x,4),round(y,4)],outline_um=[w,h],orient=orient))
    document=dict(schema='opentallas.fully_fixed_macros.v1',core_area_um=core_area,macros=expected)
    kd=Path(kd)
    (kd/'fully_fixed_macros.json').write_text(json.dumps(document,indent=1)+'\n')
    lines=['# GENERATED: explicit fully fixed macro contract; no global tool or halo change.',
           'set ::ot_fixed_macro_expected {}','set ::ot_fixed_macro_core_um {'+' '.join(map(str,core_area))+'}']
    for m in expected:
        x,y=m['origin_um'];w,h=m['outline_um']
        lines.append('dict set ::ot_fixed_macro_expected {'+m['instance']+'} {'+f"{m['master']} {x} {y} {w} {h} {m['orient']}"+'}')
    (kd/'fully_fixed_macros.tcl').write_text('\n'.join(lines)+'\n'+VALIDATOR)
    return ['export PRE_MACRO_PLACE_TCL = /work/fully_fixed_macros.tcl']
