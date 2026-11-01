#!/usr/bin/env python3
"""Plan zero-cycle VMS register affinity from actual placed connectivity.

No RTL/period/gate changes. The optional macro-street trial is an unsigned-core
plan proposal: its macro/clock-pin changes must join the parent event before
adoption. Emitted Tcl is placement-only; it never invokes STA or routing.
Run the rendered review before executing it. Existing failed results stay intact.
"""
import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'/'autopilot'))
sys.path.insert(0,str(ROOT))
import geom_rules as G
from tools.die_trial.legal_sites import RowAllocator

HALO=1.8
CELL=(1.404,.27)


def macro_boxes(D):
    return [(c[2]-HALO,c[3]-HALO,c[4]+HALO,c[5]+HALO) for c in D.cells.values() if c[0]=='M']


def kernel(D,reach):
    """Largest safe rectangle in a horizontal macro-free street, bounded against ALL outline corners."""
    x0,y0,x1,y1=D.extra['core'];W,H=D.die[2:];cx=W/2
    intervals=sorted((a[1],a[3]) for a in macro_boxes(D));merged=[]
    for lo,hi in intervals:
        if merged and lo<=merged[-1][1]:merged[-1][1]=max(hi,merged[-1][1])
        else:merged.append([lo,hi])
    ends=[y0]+[v for pair in merged for v in pair]+[y1]
    gaps=[(ends[i],ends[i+1]) for i in range(0,len(ends)-1,2) if ends[i+1]>ends[i]]
    choices=[]
    for lo,hi in gaps:
        for n in range(math.ceil(lo/.27),math.floor(hi/.27)+1):
            cy=n*.27;budget=reach-(max(cx,W-cx)+max(cy,H-cy))
            hy=min(cy-lo,hi-cy,budget/2)
            hx=min(cx-x0,x1-cx,budget-hy)
            if hx>CELL[0] and hy>CELL[1]:choices.append((4*hx*hy,(cx-hx,cy-hy,cx+hx,cy+hy),(cx,cy)))
    if not choices:raise ValueError('no macro-free reach kernel for this outline; a structural partition/stage change is needed')
    return max(choices,key=lambda q:q[0])[1:]


def plan(design,module,collect_above=380,margin=10,gap=None,family='vms'):
    D=copy.deepcopy(design)
    if not 0<=margin<405 or not 0<=collect_above<=405:
        raise ValueError('invalid planning margin/observation threshold')
    if gap is not None and gap<=0:raise ValueError('macro gap must be positive')
    if tuple(D.die[:2])!=(0.,0.):raise ValueError('core must use local0,0 coordinates')
    if not ((family=='vms' and module.startswith('hnx_vms_bank_q0_faces__vec')) or
            (family=='lane-exp' and module=='ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691')):
        raise ValueError('this planner is scoped to explicitly measured core families')
    if family!='vms' and gap is not None:
        raise ValueError('macro-street proposals are scoped to the VMS family')
    original={c[6]:c for c in D.cells.values()};byname={c[6]:i for i,c in D.cells.items()}
    out=dict(schema='opentallas.vms_reach_trial.v1',module=module,outline_um=list(D.die[2:]),prototype_only=True,
             added_cycles=0,collect_above_um=collect_above,kernel_reach_um=405-margin,macros=[],moves=[],clock_moves=[],
             review=dict(verdict='NOT_REVIEWED'),requires=['visual review before placement','full-flow PDN/taps before route',
             'parent plan event for any macro/native-clock-pin geometry change','unchanged routed signoff gates'])
    if family!='vms':out['schema']='opentallas.existing_stage_reach_trial.v1'
    if gap is not None:
        mids=sorted((i for i,c in D.cells.items() if c[0]=='M'),key=lambda i:D.cells[i][3])
        if len(mids) not in (3,4):raise ValueError('VMS trial needs the actual 3/4-SRAM inventory')
        top=max(D.cells[i][5] for i in mids)
        y=top-sum(D.cells[i][5]-D.cells[i][3] for i in mids)-gap*(len(mids)-1)
        if y<D.extra['core'][1]+HALO:raise ValueError('macro streets do not fit the existing outline')
        for i in mids:
            c=D.cells[i];h=c[5]-c[3]
            # Preserve each macro's horizontal pin-track residue (M4 pitch .048).
            yy=c[3]+round((y-c[3])/.048)*.048
            D.cells[i]=(*c[:3],yy,c[4],yy+h,c[6])
            out['macros'].append(dict(inst=c[6],xy=[c[2],round(yy,6)],size=[c[4]-c[2],h]))
            y=yy+h+gap
    bounds,centre=kernel(D,405-margin);out['kernel_um']=list(bounds)
    blocked=macro_boxes(D)
    A=RowAllocator(bounds,blocked=blocked,cell_size=CELL,column_pitch=2.16,row_pitch=.27,origin=D.extra['core'][:2])
    B=RowAllocator(D.extra['core'],blocked=blocked+[bounds],cell_size=CELL,column_pitch=2.16,row_pitch=.27,origin=D.extra['core'][:2])
    moved={};glob=set()
    def eligible(n):
        return (n in byname and D.cells[byname[n]][0]=='S' and not n.startswith(('u_bin_','u_bout_'))
                and D.extra.get('status',{}).get(byname[n]) not in {'FIRM','LOCKED','COVER'})
    def assign(n,allocator,target,why):
        i=byname[n];old=original[n];site,_=allocator.allocate(target,1,max_radius_um=sum(D.die[2:]));cx,cy=map(float,site[0])
        # Allocator uses max-size centres; preserve each real master's dimensions.
        w,h=old[4]-old[2],old[5]-old[3];x,y=cx-w/2,cy-h/2
        D.cells[i]=(old[0],old[1],x,y,x+w,y+h,old[6]);moved[n]=dict(inst=n,xy=[round(x,6),round(y,6)],reason=why)
    pairs=[];G.r2r_metrics(D,capture_pairs=pairs,collect_above=collect_above)
    todo={p[k] for p in pairs for k in ('launch','capture') if eligible(p[k])}
    for n in sorted(todo):assign(n,A,centre,'existing long sequential endpoint');glob.add(n)
    # A new macro plan must not let legalization scatter newly covered state.
    for n,c in original.items():
        if not eligible(n) or n in moved:continue
        x,y=G.ctr(c)
        if any(a<x<b and q<y<r for a,q,b,r in blocked):assign(n,B,(x,y),'state covered by revised macro plan')
    # The delivered rn stage stays local; only the actual first two synchronizers go to the input pin.
    rp=next((p for p in D.pins if p['name']=='rst_n'),None)
    if rp:
        for n in sorted(original):
            if eligible(n) and re.search(r'\.rst_s[12]\$',n):assign(n,B,(rp['x'],rp['y']-12),'first reset synchronizer near native input')
    # Re-evaluate the SAME exact census on proposed coordinates. A kernel endpoint
    # is within the stated reach of every outline point, so these moves terminate.
    for step in range(3):
        remaining=[];metrics=G.r2r_metrics(D,capture_pairs=remaining,collect_above=collect_above)
        new={p[k] for p in remaining for k in ('launch','capture') if eligible(p[k]) and p[k] not in glob}
        if not new:break
        for n in sorted(new):assign(n,A,centre,'new long endpoint after proposed placement');glob.add(n)
    metrics=G.r2r_metrics(D)
    if metrics['r2r_captures_gt405']:raise ValueError(f'proposed coordinates retain {metrics["r2r_captures_gt405"]} long captures')
    out['predicted_r2r']=metrics;out['moves']=list(moved.values())
    if gap is not None:
        cy=round(centre[1]/.048)*.048
        for p in D.pins:
            if p['sig']=='CLOCK' or G.CLOCK_PIN_RE.search(p['name']):out['clock_moves'].append(dict(port=p['name'],old_xy=[p['x'],p['y']],new_y=cy))
    out['cell_count']=len(out['moves']);return out


def tcl(spec):
    lines=['read_db /work/base.odb','set b [ord::get_db_block]','set dbu [$b getDbUnitsPerMicron]']
    for item in spec['macros']+spec['moves']:
        name=item['inst'];x,y=item['xy'];macro='size' in item
        lines+=['set i [$b findInst {'+name+'}]','if {$i eq "NULL"} {error "VMS_REACH_INSTANCE_MISSING"}','$i setPlacementStatus PLACED',
                f'$i setLocation [expr {{int(round({x}*$dbu))}}] [expr {{int(round({y}*$dbu))}}]']
        if macro:lines+=['$i setPlacementStatus LOCKED']
    for p in spec['clock_moves']:
        dy=p['new_y']-p['old_xy'][1]
        lines+=['set bt [$b findBTerm {'+p['port']+'}]','if {$bt eq "NULL"} {error "VMS_NATIVE_CLOCK_MISSING"}',
                'foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {','set layer [$box getTechLayer]',
                f'set dy [expr {{int(round({dy}*$dbu))}}]',
                'set x0 [$box xMin];set x1 [$box xMax];set y0 [expr {[$box yMin]+$dy}];set y1 [expr {[$box yMax]+$dy}]',
                'odb::dbBox_destroy $box','odb::dbBox_create $bp $layer $x0 $y0 $x1 $y1','}}']
    if spec['macros']:
        W,H=spec['outline_um']
        lines+=['foreach i [$b getInsts] {if {[regexp {^(TAPCELL|FILLER|FILL|DECAP)} [[$i getMaster] getName]]} {',
                'foreach it [$i getITerms] {if {[[$it getMTerm] getSigType] ni {POWER GROUND}} {error "PHYSICAL_TAP_HAS_SIGNAL"}}',
                'odb::dbInst_destroy $i','}}',
                f'initialize_floorplan -die_area {{0 0 {W} {H}}} -core_area {{4.32 4.32 {W-4.32} {H-4.32}}} -site asap7sc7p5t',
                'cut_rows -halo_width_x 2.16 -halo_width_y 2.16']
    lines+=['detailed_placement','write_db /work/affinity.odb','set ::env(OT_GEOM_OUT) /work/affinity.tsv','source /work/geom_dump.tcl']
    return '\n'.join(lines)+'\n'



def pre_dpl_hook(spec):
    """Emit only measured existing-FF moves, for an explicit normal-flow opt-in.

    Call after existing face/guide releases and before detailed placement. The
    exact source view and rendered plan still need kit-owner adoption; this
    emitter neither installs the hook nor releases any geometry failure.
    """
    if spec['macros'] or spec['clock_moves']:
        raise ValueError('pre-DPL hook cannot change macros or native clock pins')
    W,H=spec['outline_um'];rows=[];seen=set()
    for move in spec['moves']:
        n=move['inst'];x,y=move['xy']
        if (n in seen or any(c in n for c in '{}\n\r') or n.startswith(('u_bin_','u_bout_'))
                or not all(math.isfinite(v) for v in (x,y)) or not (0<=x<W and 0<=y<H)):
            raise ValueError('unsafe or duplicate existing-register anchor')
        seen.add(n);rows.append('  {'+n+'} '+str(x)+' '+str(y))
    lines=['# VMS measured existing-register affinity; explicit per-source-view opt-in.',
           '# Source after face/guide releases, before normal DPL; adds no cells/cycles.',
           'namespace eval ::ot_vms_affinity {',
           'set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]',
           'set die [$block getDieArea]',
           f'if {{[$die xMin] != 0 || [$die yMin] != 0 || abs([$die xMax]/double($dbu)-{W})>0.001 || abs([$die yMax]/double($dbu)-{H})>0.001}} {{error "VMS_AFFINITY_OUTLINE_MISMATCH"}}',
           'set anchors {']+rows+['}',
           '# Validate the entire exact-name contract before changing the database.',
           'foreach {name x y} $anchors {',
           '  set inst [$block findInst $name]',
           '  if {$inst eq "NULL"} {error "VMS_AFFINITY_INSTANCE_MISSING: $name"}',
           '  if {[[$inst getMaster] isBlock] || [$inst getPlacementStatus] in {FIRM LOCKED COVER}} {error "VMS_AFFINITY_ANCHOR_CONFLICT: $name"}',
           '}',
           'foreach {name x y} $anchors {',
           '  set inst [$block findInst $name]',
           '  $inst setLocation [expr {int(round($x*$dbu))}] [expr {int(round($y*$dbu))}]',
           '  $inst setPlacementStatus PLACED',
           '}',
           'puts "OT_VMS_AFFINITY applied [expr {[llength $anchors]/3}] existing-register anchors"',
           '}', 'namespace delete ::ot_vms_affinity']
    return '\n'.join(lines)+'\n'


def render(spec,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(5,7));W,H=spec['outline_um']
    for p in spec['macros']:ax.add_patch(Rectangle(p['xy'],*p['size'],color='.8'))
    for p in spec['moves']:ax.scatter(*p['xy'],s=3,color='#ad0000')
    k=spec['kernel_um'];ax.add_patch(Rectangle(k[:2],k[2]-k[0],k[3]-k[1],fill=False,edgecolor='#008000'))
    for p in spec['clock_moves']:ax.scatter(p['old_xy'][0],p['new_y'],marker='*',s=30,color='#0044aa')
    changed=spec.get('macro_plan_changed',bool(spec['macros'] or spec['clock_moves']))
    ax.set_xlim(0,W);ax.set_ylim(0,H);ax.set_aspect('equal');ax.set_title(f'Existing-stage affinity: {spec["cell_count"]} registers\n0 added cycles; '+('parent event owed for changed macro/clock plan' if changed else 'unchanged macro and clock plan'))
    fig.tight_layout();fig.savefig(path,dpi=140);plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dump',type=Path);p.add_argument('--module',required=True)
    p.add_argument('--family',choices=['vms','lane-exp'],default='vms')
    p.add_argument('--out',type=Path,required=True);p.add_argument('--macro-gap',type=float);p.add_argument('--margin',type=float,default=10)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);D=G.Design(a.dump)
    result=plan(D,a.module,margin=a.margin,gap=a.macro_gap,family=a.family)
    if not result['macros']:
        result['render_macros']=[dict(xy=[c[2],c[3]],size=[c[4]-c[2],c[5]-c[3]]) for c in D.cells.values() if c[0]=='M']
    (a.out/'plan.json').write_text(json.dumps(result,indent=1)+'\n');(a.out/'apply.tcl').write_text(tcl(result))
    if not result['macros'] and not result['clock_moves']:
        (a.out/'affinity_pre_dpl.tcl').write_text(pre_dpl_hook(result))
    r=copy.deepcopy(result)
    r['macro_plan_changed']=bool(result['macros'] or result['clock_moves'])
    if not r['macros']:r['macros']=r.get('render_macros',[])
    render(r,a.out/'plan.png');print(f'PLANNED {result["cell_count"]} registers; predicted r2r {result["predicted_r2r"]["r2r_max"]} um; NOT REVIEWED')

if __name__=='__main__':main()
