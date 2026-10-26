#!/usr/bin/env python3
"""Route planned FT wire segments, retaining station boundaries as abstract pins.

This diagnostic adds D/Q terminals at the existing planned register locations.
It does not instantiate extra logic, move plan pins/cores or change capacity.
Use --part for a small flat-vs-segmented comparison before a whole die run.
It is routing evidence only: real cell access and timing remain G2/G3 obligations.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import die_trial as DT
import gen_phys
import ft_bit_sites
import schema as S
import g2


def station_sites(P, tn, slot, bits):
    """Match G2/face-flop semantics: stage0 at input, metadata stages1..k-1."""
    pins={bit:(x,y,f) for bus,bit,layer,x,y,f in gen_phys.type_pins(P,tn) if bus==slot['name']+'_i'}
    sites=[]
    ft_bit_sites.validate_slot(slot)
    if not slot.get('bit_sites_um'):
        raise ValueError(f"{tn}/{slot['name']} has no explicit bit_sites_um")
    for j in range(int(slot.get('stations',1))):
        row=[]
        for bit in range(bits):
            if j:
                row.append(list(slot['bit_sites_um'][j-1][bit]))
            else:
                x,y,f=pins[bit];d=g2.FLOP_INSET_UM
                row.append(list({'E':(x-d,y),'W':(x+d,y),'N':(x,y-d),'S':(x,y+d)}[f]))
        sites.append(row)
    return sites


def pin(name,d,x,y):
    # Local cell access is abstracted on the permitted horizontal/vertical
    # layers; this creates no obstacle and no guide beyond the given point.
    return f'''  PIN {name}
    DIRECTION {d} ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT {x-.012:.5f} {y-.012:.5f} {x+.012:.5f} {y+.012:.5f} ;
      LAYER M5 ;
        RECT {x-.012:.5f} {y-.012:.5f} {x+.012:.5f} {y+.012:.5f} ;
    END
  END {name}
'''


def build(plan,out,part=None,segmented=False,slots=None):
    raw=S.load(plan);P=S.Plan(raw,Path(plan));out=Path(out)
    if part:
        P.parts={part:P.parts[part]}
        tn=P.parts[part]['type'];P.types={tn:P.types[tn]}
    for x in ['abstracts','grt']:(out/x).mkdir(parents=True,exist_ok=True)
    bits={};tables={};lefs=[];stats={}
    for tn,t in sorted(P.types.items()):
        b=defaultdict(int)
        for bus,bit,*_ in gen_phys.type_pins(P,tn):b[bus]=max(b[bus],bit+1)
        bits[tn]=dict(b);tables[tn]={}
        lef,st=DT.abstract_lef(P,tn)
        add=''
        if segmented:
            for sl in t.get('ft_slots',[]):
                if slots and sl['name'] not in slots:continue
                k=min(b[sl['name']+'_i'],b[sl['name']+'_o'])
                if not k:continue
                xy=station_sites(P,tn,sl,k);tables[tn][sl['name']]=xy
                for j,row in enumerate(xy):
                    for bit,(x,y) in enumerate(row):
                        add+=pin(f"ot_s_{sl['name']}_{j}_d[{bit}]",'INPUT',x,y)
                        add+=pin(f"ot_s_{sl['name']}_{j}_q[{bit}]",'OUTPUT',x,y)
        if add:lef=lef.replace('  OBS',add+'  OBS',1)
        # Type-specific abstract master identity avoids aliasing different pin
        # tables with the same RTL master; geometry comes from the same type.
        master='ot_seg_'+DT.sv(tn)
        lef=lef.replace('MACRO '+t['module']+'\n','MACRO '+master+'\n').replace('END '+t['module']+'\n','END '+master+'\n')
        t['module']=master
        fn=master+'.lef';(out/'abstracts'/fn).write_text(lef);lefs.append(fn)
        stats[tn]=dict(original_pins=st['pins'],core_obs_layers=st['core_top_layers'],station_data_pins=sum(2*len(row) for rows in tables[tn].values() for row in rows))
    v=[f'module {DT.sv(P.name)}_route (rst_n);','  input rst_n;'];instances=[];segments=0;original=0
    for n,p in sorted(P.parts.items()):
        tn=p['type'];t=P.types[tn];conns=['.arst_n(rst_n)']
        for sl in t.get('ft_slots',[]):
            sn=sl['name'];k=min(bits[tn].get(sn+'_i',0),bits[tn].get(sn+'_o',0))
            if not k:continue
            original+=k;base=f'ft_{DT.sv(n)}__{DT.sv(sn)}'
            xy=tables[tn].get(sn)
            if not xy:
                v.append(f'  wire [{k-1}:0] {base};');conns += [f'.{sn}_i({base})',f'.{sn}_o({base})'];segments+=k;continue
            for j in range(len(xy)+1):v.append(f'  wire [{k-1}:0] {base}_{j};')
            conns += [f'.{sn}_i({base}_0)',f'.{sn}_o({base}_{len(xy)})']
            for j in range(len(xy)):
                conns += [f'.ot_s_{sn}_{j}_d({base}_{j})',f'.ot_s_{sn}_{j}_q({base}_{j+1})']
            segments+=(len(xy)+1)*k
        instances.append(f'  {t["module"]} {DT.sv(n)} ({", ".join(conns)});')
    (out/'grt/route.v').write_text('\n'.join(v+instances+['endmodule'])+'\n')
    (out/'grt/tracks.tcl').write_text(DT.coarse_tracks(P,.72))
    adjust=[(f'M{i}',.75) for i in range(4,8)]+[('M8',.4),('M9',.4)]
    tcl=DT.grt_tcl(P,out/'grt',.72,lefs,[],adjust).replace('-congestion_iterations 50','-congestion_iterations 5')
    (out/'grt/grt.tcl').write_text(tcl)
    result=dict(die_trial_sha256=hashlib.sha256(Path(DT.__file__).read_bytes()).hexdigest(),plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest(),part=part,segmented=segmented,original_ft_bits=original,wire_segments=segments,adjust=dict(adjust),types=stats,added_data_cycles=0,qualification='ROUTING_DIAGNOSTIC_ONLY')
    (out/'station_probe.json').write_text(json.dumps(result,indent=2))
    (out/'station_sites.json').write_text(json.dumps(tables))
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--part');a.add_argument('--slot',action='append');a.add_argument('--segmented',action='store_true')
    p=a.parse_args();print(json.dumps(build(p.plan,p.out,p.part,p.segmented,p.slot)))
