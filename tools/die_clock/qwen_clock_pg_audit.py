#!/usr/bin/env python3
"""Read actual clock PG pins/mesh and canonical fixed-placement constraints.

This does not create rails or relocate clocks. A safe site must be selected
before clock topology; the movable-constant PDN flow cannot be reused blindly.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def audit(a):
    from openroad import Tech,Design
    tech=Tech();design=Design(tech);design.readDb(a.odb);block=design.getBlock();u=block.getDbUnitsPerMicron()
    manifest=json.loads(Path(a.manifest).read_text());die=block.getDieArea();pitch=round(8.64*u)
    phases={}
    for netname in ('VDD','VSS'):
        net=block.findNet(netname)
        if net is None:raise ValueError('actual supply net missing: '+netname)
        long=[]
        for sw in net.getSWires():
            for wire in sw.getWires():
                if wire.isVia() or wire.getTechLayer().getName()!='M8':continue
                if wire.xMax()-wire.xMin()>(die.xMax()-die.xMin())/2:
                    long.append((wire.yMin(),wire.yMax()))
        c=Counter(y0%pitch for y0,_ in long);widths=Counter(y1-y0 for y0,y1 in long)
        if len(c)!=1 or len(widths)!=1:raise ValueError('ambiguous actual core M8 phase/width '+str((netname,c,widths)))
        phases[netname]=dict(edge_dbu=next(iter(c)),width_dbu=next(iter(widths)),samples=len(long))
    halo=round(1.08*u);clear=.6*u;bins=defaultdict(list);unit=round(100*u)
    for inst in block.getInsts():
        if not (inst.getMaster().isBlock() or inst.getMaster().isPad()):continue
        q=inst.getBBox();r=(q.xMin()-halo,q.yMin()-halo,q.xMax()+halo,q.yMax()+halo)
        for x in range(r[0]//unit,(r[2]-1)//unit+1):
            for y in range(r[1]//unit,(r[3]-1)//unit+1):bins[x,y].append((inst.getName(),r))
    missing=[];phase_bad=[];halo_bad=[];pg_count=0;cells=[]
    for name,*_ in manifest['cells']:
        inst=block.findInst(name);q=inst.getBBox();r=(q.xMin(),q.yMin(),q.xMax(),q.yMax());bad=set()
        for x in range(r[0]//unit,(r[2]-1)//unit+1):
            for y in range(r[1]//unit,(r[3]-1)//unit+1):
                for other,b in bins[x,y]:
                    if r[0]<b[2] and b[0]<r[2] and r[1]<b[3] and b[1]<r[3]:bad.add(other)
        if bad:halo_bad.append(dict(cell=name,obstacles=sorted(bad)))
        rails=[]
        for pin in inst.getITerms():
            sig=str(pin.getMTerm().getSigType())
            if sig not in ('POWER','GROUND'):continue
            pg_count+=1;pn=pin.getMTerm().getName();net=pin.getNet()
            if net is None:missing.append(name+'/'+pn)
            expected='VDD' if sig=='POWER' else 'VSS';opposite='VSS' if expected=='VDD' else 'VDD'
            bb=pin.getBBox();yc=(bb.yMin()+bb.yMax())/2;phase=phases[opposite]
            relative=(yc-phase['edge_dbu'])%pitch
            badphase=relative<=phase['width_dbu']+clear or relative>=pitch-clear
            if badphase:phase_bad.append(dict(pin=name+'/'+pn,y_um=yc/u,opposite=opposite))
            rails.append(dict(pin=pn,signal_type=sig,net=None if net is None else net.getName(),y_um=yc/u,canonical_phase_safe=not badphase))
        cells.append(dict(cell=name,bbox_um=[v/u for v in r],halo_safe=not bad,rails=rails))
    return dict(schema='opentallas.qwen.clock_pg_constraints.v1',odb_sha256=sha(a.odb),
                manifest_sha256=sha(a.manifest),canonical_policy_sha256=sha(a.policy),
                actual_core_m8_pitch_um=8.64,actual_core_m8_phases=phases,macro_halo_um=1.08,
                opposite_net_clear_um=.6,clock_cells=len(cells),clock_pg_pins=pg_count,
                unconnected_clock_pg_pins=len(missing),unconnected_examples=missing[:100],
                canonical_m8_phase_conflict_pins=len(phase_bad),canonical_phase_conflict_examples=phase_bad[:100],
                macro_halo_conflict_cells=len(halo_bad),macro_halo_examples=halo_bad[:100],cells=cells,
                clock_locations_changed=False,rows_created=False,rails_created=False,power_qualified=False,
                timing_qualified=False,production_admitted=False,
                actual_owner_fix=['Use PG-safe exact bays before reserving clock buffers, including halo and actual M8/M9 reach',
                                  'Keep clock instances fixed; do not relocate them as constants in ot_tie_rows',
                                  'Bind actual supply nets and generate literal M1/M2 contact plus safe upper-metal stacks',
                                  'Require power-grid continuity/short checks and repeat actual405/net/row audit before timing'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('odb','manifest','policy','out'):p.add_argument('--'+n,required=True)
    a=p.parse_args();r=audit(a);Path(a.out).write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='cells'},indent=1),flush=True)
