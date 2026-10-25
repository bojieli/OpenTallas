#!/usr/bin/env python3
"""Inactive SU M7 repeater proposal: project inserted buffers into real gap rows.

Call after repair_design and before detailed_placement, in both prototype and
production. A caller must capture newly inserted BUF/INV IDs and their intended
locations before legalization; pre-existing cells and all flop sites are fixed.
This geometry kernel does not add registers, change OBS, or authorize routing.
"""
import math


def gap_bands(type_raw, clearance=2.0):
    cores=type_raw.get('hard_cores',[])
    if not cores or any(c.get('obs_max')!='M6' for c in cores):
        raise ValueError('proposal requires actual M6-blocked hard cores')
    width,height=type_raw['outline_um']
    blocked=sorted((c['origin_um'][1],c['origin_um'][1]+c['outline_um'][1]) for c in cores)
    bands=[];lo=4.32
    for a,b in blocked:
        if a-clearance>lo:bands.append((lo,a-clearance))
        lo=max(lo,b+clearance)
    if lo<height-4.32:bands.append((lo,height-4.32))
    if not bands:raise ValueError('no real gap rows')
    return bands


def project(type_raw, x, y, cell_width=1.08, cell_height=.27, row=.27):
    """Keep the M7 ribbon x; move only to a legal gap row. Return a proposal.

    A placement adapter must legalize occupancy inside these bands and fail if
    it cannot retain x within a small local displacement. It must not send the
    instance to a side strip as a fallback. Do not infer x from the FAILED
    post-DPL location: the original repair coordinate is required.
    """
    width,height=type_raw['outline_um']
    if not 4.32<=x<=width-4.32-cell_width:raise ValueError('ribbon x outside legal core')
    sites=[]
    for lo,hi in gap_bands(type_raw):
        first=math.ceil(lo/row)*row;last=math.floor((hi-cell_height)/row)*row
        if first<=last:sites.append(min(max(round(y/row)*row,first),last))
    if not sites:raise ValueError('no row fits repeater')
    return x,min(sites,key=lambda py:abs(py-y))


def emit_tcl(type_raw):
    """One callable adapter shared by G2 and production; activation stays opt-in.

    ot_gap_before_repair; repair_design ...; ot_gap_capture_after_repair DIR;
    allocate_sites -> reviewed exact whole-cell sites -> source emit_sites_tcl;
    detailed_placement ...; ot_gap_validate_after_dpl
    The final validator is mandatory. A nonzero placement check is a gate failure.
    """
    bands=gap_bands(type_raw)
    cores=[]
    for c in type_raw['hard_cores']:
        x,y=c['origin_um'];w,h=c['outline_um'];cores.append((x,y,x+w,y+h))
    head='set ot_gap_bands {'+' '.join('{'+ ' '.join(map(str,b))+'}' for b in bands)+'}\n'
    head+='set ot_gap_cores {'+' '.join('{'+ ' '.join(map(str,b))+'}' for b in cores)+'}\n'
    return head+r"""
# INACTIVE until explicitly sourced by BOTH prototype and production caller.
proc ot_gap_before_repair {} {
  global ot_gap_old ot_gap_moved
  array unset ot_gap_old; array unset ot_gap_moved
  foreach i [[ord::get_db_block] getInsts] { set ot_gap_old([$i getName]) 1 }
}
proc ot_gap_capture_after_repair {outdir} {
  global ot_gap_old
  if {![array exists ot_gap_old]} { error "gap adapter requires before-repair ID capture" }
  file mkdir $outdir
  write_db $outdir/pre_dpl.odb
  write_def $outdir/pre_dpl.def
  set fh [open $outdir/cells.tsv w]
  foreach i [[ord::get_db_block] getInsts] {
    set nm [$i getName]; set b [$i getBBox]
    set fresh [expr {![info exists ot_gap_old($nm)] && [regexp {^(BUF|INV)} [[$i getMaster] getName]]}]
    puts $fh "$nm\t[[$i getMaster] getName]\t[$b xMin]\t[$b yMin]\t[$b xMax]\t[$b yMax]\t$fresh"
  }
  close $fh
  puts "OT_GAP exact post-repair/pre-DPL capture $outdir"
}
# Allocate via this module's allocate_sites using the captured actual cells and
# DEF rows. Source emit_sites_tcl output ONLY after geometry review. There is no
# nearest-gap point-only fallback: all whole cells must fit actual unoccupied sites.
proc ot_gap_validate_after_dpl {{max_dx 4.0}} {
  global ot_gap_moved ot_gap_bands
  set block [ord::get_db_block]; set dbu [$block getDbUnitsPerMicron]
  set failures {}
  foreach nm [array names ot_gap_moved] {
    set i [$block findInst $nm]
    if {$i eq "NULL"} { lappend failures "$nm:missing"; continue }
    set b [$i getBBox]; set x [expr {[$b xMin]/double($dbu)}]; set y [expr {[$b yMin]/double($dbu)}]
    set h [expr {[$b dy]/double($dbu)}]; set oldx [lindex $ot_gap_moved($nm) 0]
    set fit 0
    foreach band $ot_gap_bands { lassign $band lo hi; if {$y>=$lo-1e-6 && $y+$h<=$hi+1e-6} { set fit 1 } }
    if {!$fit || abs($x-$oldx)>$max_dx} { lappend failures "$nm:x=$x,y=$y,oldx=$oldx" }
  }
  # Mandatory OpenDP legal-row / overlap / core-blockage check, no waiver.
  check_placement -verbose
  if {[llength $failures]} { error "gap adapter post-DPL failures [llength $failures]: [lrange $failures 0 9]" }
  puts "OT_GAP post-DPL PASS [array size ot_gap_moved] repeaters within real gaps and $max_dx um ribbon x"
}
"""


def allocate_sites(type_raw, cells, rows, max_dx=4.0):
    """Place actual newly inserted whole cells on actual rows without overlaps.

    cells: name, bbox_um[4], is_new_buffer; rows: x_um,y_um,step_um,count,orient.
    Return sites without mutating geometry. Every failure aborts the proposal.
    """
    bands=gap_bands(type_raw)
    boxes=[(*c['origin_um'],c['origin_um'][0]+c['outline_um'][0],
            c['origin_um'][1]+c['outline_um'][1]) for c in type_raw['hard_cores']]
    def intersects(a,b):
        return a[0]<b[2]-1e-9 and a[2]>b[0]+1e-9 and a[1]<b[3]-1e-9 and a[3]>b[1]+1e-9
    movers=[c for c in cells if c['is_new_buffer'] and any(intersects(c['bbox_um'],b) for b in boxes)]
    names={c['name'] for c in movers}
    usable=[r for r in rows if any(a-1e-8<=r['y_um'] and r['y_um']+.27<=b+1e-8 for a,b in bands)]
    used={r['y_um']:[] for r in usable}
    for c in cells:
        if c['name'] in names:continue
        x,y,x1,y1=c['bbox_um']
        for r in usable:
            if y<r['y_um']+.27-1e-8 and y1>r['y_um']+1e-8:used[r['y_um']].append((x,x1))
    out=[]
    for c in sorted(movers,key=lambda c:(c['bbox_um'][0],c['bbox_um'][1])):
        x,y,x1,y1=c['bbox_um'];w=x1-x;h=y1-y
        if abs(h-.27)>1e-6:raise ValueError('adapter currently supports actual one-row repeaters only')
        found=None
        for r in sorted(usable,key=lambda r:abs(r['y_um']-y)):
            sx=r['x_um']+round((x-r['x_um'])/r['step_um'])*r['step_um']
            if abs(sx-x)>max_dx or sx<r['x_um']-1e-8 or sx+w>r['x_um']+r['step_um']*r['count']+1e-8:continue
            if any(sx<b-1e-8 and sx+w>a+1e-8 for a,b in used[r['y_um']]):continue
            found=dict(name=c['name'],x_um=sx,y_um=r['y_um'],orient=r['orient'],width_um=w,height_um=h,
                       intended_x_um=x,intended_y_um=y)
            used[r['y_um']].append((sx,sx+w));break
        if found is None:raise ValueError(f"no nonoverlapping real row/site near ribbon x for {c['name']}")
        out.append(found)
    return out


def emit_sites_tcl(sites):
    """Exact allocation application; generated from captured graph, rows, occupancy."""
    lines=['# Inactive until this exact allocation/image has independent geometry review.',
           'array unset ot_gap_moved', 'set ot_gap_blk [ord::get_db_block]',
           'set ot_gap_dbu [$ot_gap_blk getDbUnitsPerMicron]']
    for s in sites:
        name=s['name']
        if any(c in name for c in '{};\n\r$[]'):raise ValueError('unsafe Tcl instance name')
        orient={'N':'R0','FS':'MX'}.get(s['orient'])
        if orient is None:raise ValueError('unsupported row orientation')
        lines += [f'set ot_gap_i [$ot_gap_blk findInst {{{name}}}]',
                  'if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }',
                  f'$ot_gap_i setOrient {orient}',
                  f'$ot_gap_i setLocation [expr {{round({s["x_um"]}*$ot_gap_dbu)}}] [expr {{round({s["y_um"]}*$ot_gap_dbu)}}]',
                  '$ot_gap_i setPlacementStatus FIRM',
                  f'set ot_gap_moved({name}) [list {s["intended_x_um"]} {s["y_um"]} {s["width_um"]} {s["height_um"]}]']
    return '\n'.join(lines)+'\n'
