#!/usr/bin/env python3
"""B2 F trial: compose actual ENG r5 pins and re-solve parent attachments.

No RTL changes. Parent xtier_i0 and unit_i1 each gain one registered stage;
these stages must be materialized in bound RTL and priced before adoption.
The generated abstract is a PLANNING candidate, not a SIGNED core view.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',type=Path);ap.add_argument('--plan',default='physical/die_plan/s81/die_plan.json')
    ap.add_argument('--pins',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--receipt',type=Path,required=True);a=ap.parse_args()
    d=a.root/'physical/die_plan/s81';sys.path.insert(0,str(d));import gen_plan_v4 as g
    from tools.die_plan import schema as S
    raw=json.loads((a.root/a.plan).read_text());t=raw['partition_types']['eng__t1']
    c=next(c for c in t['hard_cores'] if c['module']=='dsdv_eng_rr_e')
    oldpins=json.loads((d/c['pins_file']).read_text())['pins'];new=[]
    provided=json.loads(a.pins.read_text())
    if isinstance(provided,dict):
        new=copy.deepcopy(provided['pins'])
    else:
        for p in provided:
            new.append(dict(name=p['bus']+(f'[{p["bit"]}]' if p.get('bit') is not None else ''),layer=p['layer'],x=p['x'],y=p['y']))
    assert {p['name'] for p in new}=={p['name'] for p in oldpins},'core pin names changed'
    oldmap={p['name']:p for p in oldpins};moved=sum(any(p[k]!=oldmap[p['name']][k] for k in ('x','y','layer')) for p in new)
    rel='inputs/core_pins/dsdv_eng_rr_e_r5_candidate.json';pp=d/rel
    pp.write_text(json.dumps(dict(module=c['module'],source='ENG r5 actual-placement pin recipe; NOT SIGNED',pins=new),indent=1)+'\n')
    oldlef=a.root/c['lef'];text=oldlef.read_text();blocks={}
    for match in re.finditer(r'(?ms)^  PIN (\S+)\n(.*?)^  END \1\s*$',text):blocks[match[1]]=match.group(2)
    lines=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {c["module"]}','  CLASS BLOCK ;','  ORIGIN 0 0 ;',f'  SIZE {c["outline_um"][0]} BY {c["outline_um"][1]} ;','  SYMMETRY X Y ;']
    for p in new:
        body=blocks[p['name']];direction=re.search(r'DIRECTION (\w+)',body).group(1);use=re.search(r'USE (\w+)',body).group(1)
        x,y=p['x'],p['y'];lines += [f'  PIN {p["name"]}',f'    DIRECTION {direction} ;',f'    USE {use} ;','    PORT',f'      LAYER {p["layer"]} ;',f'      RECT {x-.012:.6f} {y-.012:.6f} {x+.012:.6f} {y+.012:.6f} ;','    END',f'  END {p["name"]}']
    for n,body in blocks.items():
        if n not in {p['name'] for p in new}:lines += [f'  PIN {n}',body.rstrip(),f'  END {n}']
    lines += ['  OBS']
    for i in range(1,6):lines += [f'    LAYER M{i} ;',f'      RECT 0 0 {c["outline_um"][0]} {c["outline_um"][1]} ;']
    lines += ['  END',f'END {c["module"]}','END LIBRARY']
    lef=d/'cores/eng/lef/dsdv_eng_rr_e_r5_candidate.lef';lef.write_text('\n'.join(lines)+'\n')
    c['pins_file']=rel;c['lef']=str(lef.relative_to(a.root))
    before=copy.deepcopy(t['internal_stations']);entries,_=g.core_internal_stations('eng',t['hard_cores'],*t['outline_um'],t['buses'])
    # Bus-centre checks alone miss24 actual vi_s bit paths at415.806um. Add
    # a real parent station for the whole coherent276-bit bus (R8).
    group=g._placed_groups(c)[1]['vi_s'];fr=g._bus_pts(t['buses'],*t['outline_um'])['xtier_i0'];to=group[:2]
    reg=[round((fr[0]+to[0])/2,3),round((fr[1]+to[1])/2,3)]
    entries.append(dict(conn='bus:xtier_i0',from_um=list(fr),to_um=list(to),regs_um=[reg],bits=276,
        launch='face bus xtier_i0',capture='u_eng.u_e.vi_s',note='Exact parent face/core bit census found24 paths >405um (max415.806); one coherent input station, +1 data cycle.'))
    t['internal_stations']=entries
    stations={e['conn']:e['regs_um'] for e in entries};pmap={p['name']:p for p in new};layers={v['name']:v for v in S.ASAP7_LAYERS};rows=[]
    for pa,bn in [('pci','unit_i0'),('rco','unit_o0'),('f_ks','unit_i1'),('vi_s','xtier_i0'),('vo_s','xtier_o0'),('vo_n','xtier_o1'),('vi_n','xtier_i1')]:
        bus=next(v for v in t['buses'] if v['name']==bn);b=dict(bus,id=bn,src={'part':'eng'},dst={'part':'svc_14'})
        bp={i:(coord,t['outline_um'][1]) for i,ln,coord in S.pin_positions(b,layers)};maxhop=0;bad=0;n=0
        for key,p in pmap.items():
            match=re.fullmatch(re.escape(pa)+r'\[(\d+)\]',key)
            if not match:continue
            i=int(match[1]);bi=i+4 if (pa=='pci' and i>0) or (pa=='rco' and i>=32) else i
            dst=[c['origin_um'][0]+c['track_offset_um'][0]+p['x'],c['origin_um'][1]+c['track_offset_um'][1]+p['y']]
            pts=[bp[bi]]+stations.get('bus:'+bn,[])+[dst]
            mh=max(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(pts,pts[1:]));maxhop=max(maxhop,mh);bad+=mh>405+1e-6;n+=1
        rows.append(dict(core_port=pa,bus=bn,bits=n,max_hop_um=round(maxhop,3),over405=bad))
    assert all(r['over405']==0 for r in rows),rows
    # The historical plan declared PCI2/RCO1 physical stages but did not put
    # them into fixed_cycles. Make the trial latency table authoritative too.
    pmap_plan={p['id']:p for p in raw['ports']};priced=[]
    for busname,count in ((e['conn'][4:],len(e['regs_um'])) for e in entries):
        bus=next(b for b in t['buses'] if b['name']==busname);side='dst' if bus['dir']=='in' else 'src';edge=-1 if side=='dst' else 0
        matched=[ln for ln in raw['lanes'] if pmap_plan[ln['ports'][edge]][side]=={'part':'eng','bus':busname}]
        assert len(matched)==1,(busname,matched)
        ln=matched[0];prior=int(ln.get('fixed_cycles',0));assert prior in (0,count),(ln['id'],prior,count)
        ln['fixed_cycles']=count;priced.append(dict(lane=ln['id'],bus=busname,old_fixed=prior,new_fixed=count))
    report=dict(status='PLANNING candidate; no bind/STA/signoff adoption',pins=len(new),moved=moved,
        parent_data_census=rows,old_station_counts={v['conn']:len(v['regs_um']) for v in before},
        new_station_counts={v['conn']:len(v['regs_um']) for v in entries},
        cycle_delta=dict(core_RTL=0,parent_xtier_i0=1,parent_unit_i1=1,geometry_added_cycles=2,geometry_added_bit_cycles=329,historical_unpriced_PCI_cycles=2,historical_unpriced_RCO_cycles=1,total_fixed_cycles_vs_raw_plan=5),priced_lanes=priced,
        wrapper_mapping='dsdv_eng_rr_split: pci={pci[267:5],pci[0]}; rco={rco_e[38:32],PCBASE[29:26],rco_e[31:0]}; other buses bit-identical',
        remaining=['Materialize all five parent stages in bound RTL (PCI2/RCO1 historical physical, FKS1/VI_S1 new), lockstep/mutant, and price against the previously unpriced raw calendar.',
                   'R5 engine core placement/route/signoff remains owned PATH-S81/head_eng; candidate LEF is not a signed view.'])
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(raw,separators=(',',':'))+'\n')
    a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
