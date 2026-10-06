#!/usr/bin/env python3
"""Read-only native OpenDB CP access planner; emits a pin-only owner hook.

Run with OpenROAD -python (argv after --). Does not route or write an ODB.
Canonical region/fence/PG/RTL/SDC files are never modified. Route qualification
and allocation acceptance remain Harvey/Turing's responsibilities.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

EXPECTED_BODY = sorted([(17280,17280,60480,56160),
                        (22464,56160,60480,60480),
                        (60480,17280,64800,64800),
                        (17280,60480,60480,64800)])
EXPECTED_ASSOC = [(17280,56160,22464,60480)]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rect(box):
    return [box.xMin(),box.yMin(),box.xMax(),box.yMax()]

def select_tracks(candidates, separation):
    result=[]
    for y in sorted(set(candidates)):
        if not result or y-result[-1]>=separation:
            result.append(y)
    return result

def cut_rule(tech, name):
    layer=tech.findLayer(name)
    defaults=[r.getDefault() for r in layer.getTechLayerCutSpacingTableDefRules()
              if r.isDefaultValid()]
    if not defaults:
        raise ValueError(f'{name}: no native cut-spacing default')
    # Actual single-cut dimensions, not generated power via-array pitches.
    cuts=[]
    for via in tech.getVias():
        if via.getName() not in ('VIA45','VIA56','VIA67'):
            continue
        cuts += [max(b.xMax()-b.xMin(),b.yMax()-b.yMin())
                 for b in via.getBoxes() if b.getTechLayer()==layer]
    if not cuts:
        raise ValueError(f'{name}: no default access cut')
    return {'cut_width_dbu':max(cuts),'spacing_dbu':max(defaults),
            'minimum_center_dbu':max(cuts)+max(defaults)}

def marker_summary(path, ports, dbu):
    text=Path(path).read_text()
    classes=Counter(); pinclasses=Counter(); nearwest=Counter()
    for chunk in re.split(r'(?m)(?=^violation type:)',text):
        m=re.search(r'violation type:\s*(.+)',chunk)
        if not m: continue
        layer=re.search(r'on [Ll]ayer\s+(\S+)',chunk)
        key=f'{m[1].strip()}:{layer[1] if layer else "unknown"}'
        classes[key]+=1
        nets=re.findall(r'\b(?:net|pin):([^\s]+)',chunk)
        if any(n in ports for n in nets):pinclasses[key]+=1
        bb=re.search(r'bbox = \(([-\d.]+),\s*([-\d.]+)\) - \(([-\d.]+),\s*([-\d.]+)\)',chunk)
        if bb and float(bb[1])<=17.60 and float(bb[3])>=17.20:
            nearwest[key]+=1
    return {'total':sum(classes.values()),'all_classes':dict(classes),
            'port_net_classes':dict(pinclasses),'west_strip_classes':dict(nearwest),
            'sha256':sha(path)}

def held_job_v4_diagnosis(block, tech):
    import odb
    vias={}
    for name in ('held_job[13]','held_job[14]'):
        net=block.findNet(name)
        if not net or not net.getWire(): raise ValueError('Missing retained held-job route')
        decoder=odb.dbWireDecoder();decoder.begin(net.getWire());centers=[]
        while True:
            op=decoder.next()
            if op==odb.dbWireDecoder.END_DECODE: break
            if op not in (odb.dbWireDecoder.TECH_VIA,odb.dbWireDecoder.VIA): continue
            via=decoder.getTechVia() if op==odb.dbWireDecoder.TECH_VIA else decoder.getVia()
            if any(b.getTechLayer().getName()=='V4' for b in via.getBoxes()):
                centers.append(list(decoder.getPoint()))
        vias[name]=centers
    width=cut_rule(tech,'V4')['cut_width_dbu']
    pairs=[]
    for a in vias['held_job[13]']:
        for b in vias['held_job[14]']:
            dx,dy=abs(a[0]-b[0]),abs(a[1]-b[1])
            gap=math.hypot(max(0,dx-width),max(0,dy-width))
            pairs.append({'held13_xy_dbu':a,'held14_xy_dbu':b,
                          'center_delta_dbu':[dx,dy],'cut_edge_gap_dbu':gap})
    return {'actual_vias':vias,'nearest_cut_pair':min(pairs,key=lambda p:p['cut_edge_gap_dbu']),
            'required_cut_edge_gap_dbu':cut_rule(tech,'V4')['spacing_dbu'],
            'route_requirement':'Avoid single-track (48,48) diagonal VIA45 adjacency; same-column centers need >=58DBU (96DBU on48DBU grid). Pin separation alone does not fix retained wires.'}

def pg_boxes(block):
    result=[]
    for net in block.getNets():
        if net.getSigType() not in ('POWER','GROUND'): continue
        for wire in net.getSWires():
            for box in wire.getWires():
                if box.isVia():
                    x,y=box.getViaXY()
                    via=box.getTechVia() or box.getBlockVia()
                    for b in via.getBoxes():
                        a=rect(b)
                        result.append((b.getTechLayer().getName(),
                                       [a[0]+x,a[1]+y,a[2]+x,a[3]+y]))
                else:
                    result.append((box.getTechLayer().getName(),rect(box)))
    for obs in block.getObstructions():
        b=obs.getBBox()
        result.append((b.getTechLayer().getName(),rect(b)))
    return result

def snapshot(block):
    return {'regions':{r.getName():sorted(rect(b) for b in r.getBoundaries())
                       for r in block.getRegions()},
            'groups':{g.getName():sorted(i.getName() for i in g.getInsts())
                      for g in block.getGroups()},
            'macros':sorted((i.getName(),i.getMaster().getName(),i.getOrient(),i.getLocation())
                            for i in block.getInsts() if i.getMaster().isBlock()),
            'port_nets':sorted((p.getName(),p.getNet().getName(),p.getIoType(),p.getSigType())
                              for p in block.getBTerms())}

def make_hook(pins):
    # Reuse place_pin; do not touch placement, net/ITerm connectivity, groups,
    # constraints or PG. Fail before any pin write on a different allocation.
    lines=['# Generated CP236 pin-only hook. Turing allocation; Harvey sole launch.',
           '# Source after canonical four-box + association hooks, before placement.',
           '# Do not apply to a routed checkpoint: its old wires would be stale.',
           'set ot_pin_block [ord::get_db_block]',
           'if {[$ot_pin_block getDbUnitsPerMicron]!=1000} {error "CP access units changed"}',
           'proc ot_cp_access_regions {} {',
           ' set out {}; set b [ord::get_db_block]',
           ' foreach name {cp_body cp_association} {',
           '  set r [$b findRegion $name]; if {$r eq "NULL"} {error "Missing CP fence $name"}',
           '  set boxes {}; foreach box [$r getBoundaries] {',
           '   lappend boxes [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]',
           '  }; lappend out $name [lsort $boxes]',
           ' }; return $out',
           '}',
           'set ot_pin_before [ot_cp_access_regions]',
           'set ot_pin_expected {cp_body {{17280 17280 60480 56160} {17280 60480 60480 64800} {22464 56160 60480 60480} {60480 17280 64800 64800}} cp_association {{17280 56160 22464 60480}}}',
           'if {$ot_pin_before ne $ot_pin_expected} {error "CP allocation differs"}',
           'set ot_pin_names {']
    lines += [' {'+p['name']+'}' for p in pins]
    lines += ['}',
              'foreach name $ot_pin_names {if {[$ot_pin_block findBTerm $name] eq "NULL"} {error "Missing pin $name"}}']
    for p in pins:
        x,y=p['xy_dbu'];name=p['name']
        lines.append(f'place_pin -pin_name {{{name}}} -layer M6 -location {{{x/1000:.3f} {y/1000:.3f}}}')
    lines += ['if {[ot_cp_access_regions] ne $ot_pin_before} {error "CP fences changed"}',
              'puts "OT_CP_PIN_ACCESS pins=236 M6_step_dbu=128 same_body4_association1"']
    return '\n'.join(lines)+'\n'

def main():
    import odb
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--odb',required=True);ap.add_argument('--drc',required=True)
    ap.add_argument('--inputs',required=True);ap.add_argument('--out',required=True)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
    database=odb.dbDatabase.create();odb.read_db(database,args.odb)
    block=database.getChip().getBlock();tech=database.getTech()
    before=snapshot(block);dbu=block.getDbUnitsPerMicron()
    if dbu!=1000 or before['regions'].get('cp_body')!=[list(x) for x in EXPECTED_BODY] or before['regions'].get('cp_association')!=[list(x) for x in EXPECTED_ASSOC]:
        raise ValueError('Not the actual CP four-box/association allocation')
    canonical=json.loads(Path(args.inputs).read_text())['pins']
    names=[p['name'] for p in canonical]
    actual=[p.getName() for p in block.getBTerms() if p.getSigType() not in ('POWER','GROUND')]
    if len(names)!=236 or len(set(names))!=236 or set(actual)!=set(names):
        raise ValueError('Actual signal/clock/reset BTerm inventory differs from reserved236')
    layer=tech.findLayer('M6');grid=list(block.findTrackGrid(layer).getGridY())
    pitch=layer.getPitch();rules={n:cut_rule(tech,n) for n in ('V4','V5','V6')}
    minimum=max(r['minimum_center_dbu'] for r in rules.values())
    step=math.ceil(max(minimum,layer.getWidth()+layer.getSpacing())/pitch)*pitch
    if step!=128:raise ValueError(f'Actual tech changed: re-evaluate spacing {step}')
    # Use only the west face below the association notch. All 236 fit without
    # spreading to unallocated faces or borrowing the twelve internal M7 tracks.
    x=17280;lo=17280;hi=56160
    # Single-cut access footprint through M5/M6/M7 including the observed
    # V4 landing strip at x=17.4um. PG is immutable; reject intersecting sites.
    blockers=[(l,b) for l,b in pg_boxes(block)
              if l in ('M4','M5','M6','M7','V4','V5','V6') and b[0]<=x+160 and b[2]>=x-35]
    clearance=max(r['spacing_dbu'] for r in rules.values())+27
    candidates=[y for y in grid if lo+clearance<=y<=hi-clearance
                and not any(b[1]-clearance<=y<=b[3]+clearance for _,b in blockers)]
    slots=select_tracks(candidates,step)
    if len(slots)<236:raise ValueError(f'Finite west access capacity {len(slots)} <236; Turing allocation required')
    # Clock/reset first, separated on legal native tracks; preserve ordered buses
    # and original channel order for all other signals.
    ordered=['clk','por_n']+[n for n in names if n not in ('clk','por_n')]
    pins=[{'name':n,'layer':'M6','xy_dbu':[x,y],'xy_um':[x/dbu,y/dbu]}
          for n,y in zip(ordered,slots)]
    report={'schema':'hbm.cp.pin-access.spread.v1','input_odb_sha256':sha(args.odb),
            'input_pins_sha256':sha(args.inputs),'read_only':True,
            'native_dbu_per_um':dbu,'native_M6_pitch_dbu':pitch,
            'cut_rules':rules,'selected_minimum_step_dbu':step,
            'available_face':'west M6 below association notch',
            'face_interval_dbu':[lo,hi],'PG_access_blocking_boxes':len(blockers),
            'raw_unblocked_tracks':len(candidates),'separated_capacity':len(slots),
            'used':236,'unused_capacity':len(slots)-236,
            'first_last_y_dbu':[pins[0]['xy_dbu'][1],pins[-1]['xy_dbu'][1]],
            'minimum_actual_separation_dbu':min(b['xy_dbu'][1]-a['xy_dbu'][1] for a,b in zip(pins,pins[1:])),
            'preserved_regions':before['regions'],'macro_count':len(before['macros']),
            'structural_snapshot_sha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),
            'markers':marker_summary(args.drc,set(names),dbu),
            'held_job_V4_diagnosis':held_job_v4_diagnosis(block,tech),'pins':pins,
            'cycles_added':0,'RTL_FF_added':0,'SDC_or_load_edits':False,
            'qualification':'ACCESS PLAN ONLY; DRC/STA/IR require Harvey changed-source route'}
    if snapshot(block)!=before:raise AssertionError('Read-only planning mutated database')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    (out/'pins_only.tcl').write_text(make_hook(pins))
    (out/'plan.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('used','separated_capacity','unused_capacity','first_last_y_dbu','minimum_actual_separation_dbu','markers')}))

if __name__=='__main__':main()
