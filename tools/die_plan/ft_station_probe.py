#!/usr/bin/env python3
"""Route planned FT wire segments, retaining station boundaries as abstract pins.

This diagnostic adds D/Q terminals at the existing planned register locations.
It does not instantiate extra logic, move plan pins/cores or change capacity.
Use --part for a bounded, gcell-aligned coupon before a whole die run.
--unbounded retains the historical full-canvas diagnostic only.
It is routing evidence only: real cell access and timing remain G2/G3 obligations.
"""
import argparse
import hashlib
import json
import math
import re
import sys
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
    if int(slot.get('stations',1)) > 1 and not slot.get('bit_sites_um'):
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


def build(plan,out,part=None,segmented=False,slots=None,bounded=None):
    raw=S.load(plan);P=S.Plan(raw,Path(plan));out=Path(out)
    if bounded is None:bounded=bool(part)
    if bounded and not part:raise ValueError('--bounded requires --part')
    if part:
        P.parts={part:P.parts[part]}
        tn=P.parts[part]['type'];P.types={tn:P.types[tn]}
    for x in ['abstracts','grt']:(out/x).mkdir(parents=True,exist_ok=True)
    bits={};tables={};lefs=[];stats={}
    for tn,t in sorted(P.types.items()):
        b=defaultdict(int)
        for bus,bit,*_ in gen_phys.type_pins(P,tn):b[bus]=max(b[bus],bit+1)
        bits[tn]=dict(b);tables[tn]={}
        if bounded:
            planned=[h for h in t.get('hard_cores',[]) if 'origin_um' in h and 'outline_um' in h]
            observed=DT.core_obs(t)
            if len(planned)!=len(observed) or any(h.get('obs_max') and int(r[4][1:])<int(h['obs_max'][1:]) for h,r in zip(planned,observed)):
                raise ValueError('bounded coupons require the conservative declared/view core obstruction union')
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
    coupon_canvas=None
    if bounded:
        # Preserve the original die's 10.8um GRT gcell phase and include only
        # cells touching the partition. Exact-edge cropping loses north pins
        # in OpenROAD's final fractional gcell. This is a guide-domain hull,
        # never a physical enlargement of the partition.
        bx0,by0,bx1,by1=P.rect(part);gcell=10.8
        x0,y0=math.floor((bx0-1e-7)/gcell)*gcell,math.floor((by0-1e-7)/gcell)*gcell
        x1,y1=math.ceil((bx1+1e-7)/gcell)*gcell,math.ceil((by1+1e-7)/gcell)*gcell
        x0,y0,x1,y1=max(0.,x0),max(0.,y0),min(P.W,x1),min(P.H,y1)
        coupon_canvas=[x0,y0,x1,y1]
        area=f'{x0:.6f} {y0:.6f} {x1:.6f} {y1:.6f}'
        tcl=re.sub(r'initialize_floorplan -die_area \{[^}]+\} -core_area \{[^}]+\}',f'initialize_floorplan -die_area {{{area}}} -core_area {{{area}}}',tcl)
        # The coupon reset source is local to its existing reset pin, as in G2;
        # this avoids an unrelated full-die reset wire outside the coupon.
        entry=next((q for q in gen_phys.tap_pins(P,tn) if q[0]=='arst_n'),None)
        if entry is None:raise ValueError('bounded coupon requires its real reset entry pin')
        rx,ry=P.to_die(part,entry[1:])
        tcl=re.sub(r'place_pin -pin_name rst_n -layer \S+ -location \{[^}]+\}',f'place_pin -pin_name rst_n -layer M7 -location {{{rx:.6f} {ry:.6f}}}',tcl)
        tracks=[]
        for layer in ['M1','M2','M3','M4','M5','M6','M7','M8','M9']:
            pitch=.72 if layer in ['M1','M2','M3'] else P.layers[layer]['pitch_um']
            offset=.36 if layer in ['M1','M2','M3'] else P.layers[layer]['offset_um']
            tracks.append(f'make_tracks {layer} -x_offset {(offset-x0)%pitch:.12f} -x_pitch {pitch} -y_offset {(offset-y0)%pitch:.12f} -y_pitch {pitch}')
        (out/'grt/tracks.tcl').write_text('\n'.join(tracks)+'\n')
        obs=out/'grt/obs.tcl';clipped=[]
        for line in obs.read_text().splitlines():
            m=re.search(r'-region \{([^}]+)\} -layer (M\d+)',line)
            if not m:raise ValueError('unexpected obstruction statement')
            a,b,c,d=map(float,m[1].split());a,b,c,d=max(a,x0),max(b,y0),min(c,x1),min(d,y1)
            if a<c and b<d:clipped.append(f'create_obstruction -region {{{a:.6f} {b:.6f} {c:.6f} {d:.6f}}} -layer {m[2]}')
        obs.write_text('\n'.join(clipped)+'\n')
    (out/'grt/grt.tcl').write_text(tcl)
    result=dict(die_trial_sha256=hashlib.sha256(Path(DT.__file__).read_bytes()).hexdigest(),plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest(),part=part,segmented=segmented,original_ft_bits=original,wire_segments=segments,adjust=dict(adjust),types=stats,added_data_cycles=0,qualification='ROUTING_DIAGNOSTIC_ONLY',bounded=bounded,part_bounds_um=list(P.rect(part)) if part else None,coupon_canvas_um=coupon_canvas)
    (out/'station_probe.json').write_text(json.dumps(result,indent=2))
    (out/'station_sites.json').write_text(json.dumps(tables))
    return result

def report(out):
    out=Path(out);log=(out/'run.log').read_text() if (out/'run.log').is_file() else ''
    meta=json.loads((out/'station_probe.json').read_text())
    tables=log.split('Final congestion report:')
    layers={}
    if len(tables)>1:
        for line in tables[-1].splitlines():
            m=re.match(r'\s*(M[1-9])\s+\d+\s+\d+\s+[\d.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)',line)
            if m:layers[m[1]]=dict(max_h=int(m[2]),max_v=int(m[3]),overflow=int(m[4]))
    errors={k:len(re.findall(k,log)) for k in ['GRT-0113','GRT-0114','GRT-0229']}
    complete='OT_DONE' in log and bool(re.search(r'ot-run:.*RAN on.*exit 0',log)) and {'M4','M5','M6','M7'} <= set(layers)
    overflow=sum(x['overflow'] for x in layers.values())
    boundary=None
    if meta.get('bounded'):
        guide=out/'grt/route.guide';canvas=meta['coupon_canvas_um'];box=meta['part_bounds_um']
        outside=0;max_escape=0.;net='';rectangles=0
        if not guide.is_file():complete=False
        else:
            for line in guide.read_text().splitlines():
                f=line.split()
                if len(f)==1 and f[0] not in ['(',')']:net=f[0];continue
                if len(f)!=5 or not net.startswith('ft_'):continue
                a,b,c,d=[float(v)/1000 for v in f[:4]];rectangles+=1
                outside+=int(a<canvas[0]-.001 or b<canvas[1]-.001 or c>canvas[2]+.001 or d>canvas[3]+.001)
                max_escape=max(max_escape,box[0]-a,box[1]-b,c-box[2],d-box[3])
        boundary=dict(outside_canvas_rectangles=outside,rectangles=rectangles,max_boundary_quantization_um=round(max_escape,6))
        if not rectangles:complete=False
    verdict='NOT RUN' if not complete else 'FAIL' if overflow or any(errors.values()) or (boundary and boundary['outside_canvas_rectangles']) else 'PASS' 
    w=re.findall(r'Total wirelength:\s+(\d+) um',log);n=re.findall(r'Routed nets:\s+(\d+)',log)
    result=dict(**meta,boundary=boundary,verdict=verdict,overflow=overflow if layers else None,layers=layers,grt_errors=errors,completed=complete,wire_um=int(w[-1]) if w else None,routed_nets=int(n[-1]) if n else None)
    receipt=out/'station_result.json';index=0
    while receipt.exists():
        if json.loads(receipt.read_text())==result:return result
        index+=1;receipt=out/f'station_result_{index}.json'
    receipt.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='report':
        r=report(sys.argv[2]);print(json.dumps(r));sys.exit(0 if r['verdict']=='PASS' else 1)
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--part');a.add_argument('--slot',action='append');a.add_argument('--segmented',action='store_true')
    scope=a.add_mutually_exclusive_group();scope.add_argument('--bounded',action='store_const',const=True,default=None);scope.add_argument('--unbounded',dest='bounded',action='store_const',const=False)
    p=a.parse_args();print(json.dumps(build(p.plan,p.out,p.part,p.segmented,p.slot,p.bounded)))
