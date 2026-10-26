#!/usr/bin/env python3
"""B2 F trial: compose actual ENG r5 pins and re-solve parent attachments.

No RTL changes. Parent xtier_i0 and unit_i1 each gain one registered stage;
these stages must be materialized in bound RTL and priced before adoption.
The generated abstract is a PLANNING candidate, not a SIGNED core view.
"""
import argparse
import copy
import csv
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
    raw=json.loads((a.root/a.plan).read_text())
    partmap={p['name']:p for p in raw['partitions']};portmap={p['id']:p for p in raw['ports']};abi=[]
    # Exact877 generated parent payloads: PCI264 identity; RCO39 packs38
    # core data bits plus cfgfault, while RCO valid is the separate flt bus.
    for lid,oldwidth,newwidth in (('unit__svc_14__eng',268,264),('unit__eng__svc_14',43,39)):
        lane=next(l for l in raw['lanes'] if l['id']==lid)
        for pid in lane['ports']:
            port=portmap[pid];assert port['width'] in (oldwidth,newwidth);port['width']=newwidth
            for side in ('src','dst'):
                ep=port[side];typ=partmap[ep['part']]['type'];assert sum(p['type']==typ for p in raw['partitions'])==1,(typ,'shared ABI type')
                bus=next(b for b in raw['partition_types'][typ]['buses'] if b['name']==ep['bus']);assert bus['width'] in (oldwidth,newwidth);bus['width']=newwidth
        abi.append(dict(lane=lid,before=oldwidth,after=newwidth,epoch_bit=newwidth))
    # Preserve the historical raw census. Project only the two exact live-field
    # contracts, and add the real cfgfault wrapper bit as its own source row.
    census=raw['census'][0];oldcensus=d/census['rows'];rows=list(csv.DictReader(oldcensus.open(),delimiter='\t'));fields=list(rows[0]);changes=[]
    for row in rows:
        if (row['src'],row['src_bus'],row['dst'],row['dst_bus'])==('u_etap_15','pco','u_eng','pci'):
            assert int(row['bits']) in (268,264);changes.append(dict(source='PCI consumed field projection',before=int(row['bits']),after=264));row['bits']='264'
            row['src_bus']='pco[267:5]|pco[0]';row['dst_bus']='pci_live[263:0]'
        elif (row['src'],row['src_bus'],row['dst'],row['dst_bus'])==('u_eng','rco','u_etap_15','rci'):
            assert int(row['bits']) in (43,39);changes.append(dict(source='RCO live fields, includes valid',before=int(row['bits']),after=39));row['bits']='39'
            row['src_bus']='rco[42:36]|rco[31:0]';row['dst_bus']='rci_live[38:0]'
    assert len(changes)==2,'source census projection must match exactly two historical rows'
    extra={k:'' for k in fields};extra.update(src='@generated_eng_parent',src_bus='unit_o0.d[38]=cfg_fault',dst='@generated_svc14_parent',dst_bus='unit_i1.q[38]',kind='data',bits='1');rows.append(extra)
    cpath=d/'census/s81_lanes_eng_live_1026.tsv';cpath.parent.mkdir(parents=True,exist_ok=True)
    with cpath.open('w') as f:
        writer=csv.DictWriter(f,fieldnames=fields,delimiter='\t');writer.writeheader();writer.writerows(rows)
    mp=json.loads((d/census['map']).read_text());mp['parts'].update({'@generated_eng_parent':'eng','@generated_svc14_parent':'svc_14'})
    cmap=d/'census_map_eng_live_1026.json';cmap.write_text(json.dumps(mp,indent=1)+'\n')
    census.update(rows='census/s81_lanes_eng_live_1026.tsv',map='census_map_eng_live_1026.json',note='Historical rows preserved separately; exact877 generated parent live PCI264/RCO39 projection plus explicit real cfg_fault wrapper metadata bit; source mapping in eng_r5_parent_census_1026_v5.json. No padding exemption.')
    t=raw['partition_types']['eng__t1']
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
    valid=next(p for p in new if p['name']=='rco[0]');valid_to=[c['origin_um'][0]+c['track_offset_um'][0]+valid['x'],c['origin_um'][1]+c['track_offset_um'][1]+valid['y']]
    valid_fr=g._bus_pts(t['buses'],*t['outline_um'])['flt_o0'];valid_reg=[round((valid_fr[i]+valid_to[i])/2,3) for i in (0,1)]
    entries.append(dict(conn='bus:flt_o0',from_um=list(valid_fr),to_um=valid_to,regs_um=[valid_reg],bits=1,launch='face bus flt_o0',capture='u_eng.u_e.rco',note='Exact source RCOvalid core_rco[0]; match the RCOdata parent output stage age, +1 parallel valid cycle.'))
    t['internal_stations']=entries
    stations={e['conn']:e['regs_um'] for e in entries};pmap={p['name']:p for p in new};layers={v['name']:v for v in S.ASAP7_LAYERS};rows=[]
    for pa,bn in [('pci','unit_i0'),('rco','unit_o0'),('f_ks','unit_i1'),('vi_s','xtier_i0'),('vo_s','xtier_o0'),('vo_n','xtier_o1'),('vi_n','xtier_i1')]:
        bus=next(v for v in t['buses'] if v['name']==bn);b=dict(bus,id=bn,src={'part':'eng'},dst={'part':'svc_14'})
        bp={i:(coord,t['outline_um'][1]) for i,ln,coord in S.pin_positions(b,layers)};maxhop=0;bad=0;n=0
        for key,p in pmap.items():
            match=re.fullmatch(re.escape(pa)+r'\[(\d+)\]',key)
            if not match:continue
            i=int(match[1])
            if pa=='rco' and i==0:continue
            bi=i-1 if pa=='rco' else i;actual_bn=bn;actual_bp=bp
            if pa=='rco' and i==0:
                actual_bn='flt_o0';vb=next(v for v in t['buses'] if v['name']==actual_bn);vp=dict(vb,id=actual_bn,src={'part':'eng'},dst={'part':'svc_14'})
                actual_bp={j:(coord,t['outline_um'][1]) for j,ln,coord in S.pin_positions(vp,layers)};bi=0
            dst=[c['origin_um'][0]+c['track_offset_um'][0]+p['x'],c['origin_um'][1]+c['track_offset_um'][1]+p['y']]
            pts=[actual_bp[bi]]+stations.get('bus:'+actual_bn,[])+[dst]
            mh=max(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(pts,pts[1:]));maxhop=max(maxhop,mh);bad+=mh>405+1e-6;n+=1
        rows.append(dict(core_port=pa,bus=bn,bits=n,max_hop_um=round(maxhop,3),over405=bad))
    assert all(r['over405']==0 for r in rows),rows
    vb=next(v for v in t['buses'] if v['name']=='flt_o0');vp=dict(vb,id='flt_o0',src={'part':'eng'},dst={'part':'svc_14'})
    vpin=next(coord for i,ln,coord in S.pin_positions(vp,layers) if i==0)
    vpts=[[vpin,t['outline_um'][1]]]+stations['bus:flt_o0']+[valid_to]
    vh=max(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(vpts,vpts[1:]))
    assert vh<=405+1e-6
    rows.append(dict(core_port='rco[0] VALID',bus='flt_o0',bits=1,max_hop_um=round(vh,3),over405=0))
    # The historical plan declared PCI2/RCO1 physical stages but did not put
    # them into fixed_cycles. Make the trial latency table authoritative too.
    pmap_plan={p['id']:p for p in raw['ports']};priced=[]
    for busname,count in ((e['conn'][4:],len(e['regs_um'])) for e in entries):
        bus=next(b for b in t['buses'] if b['name']==busname);side='dst' if bus['dir']=='in' else 'src';edge=-1 if side=='dst' else 0
        matched=[ln for ln in raw['lanes'] if pmap_plan[ln['ports'][edge]][side]=={'part':'eng','bus':busname}]
        assert len(matched)==1,(busname,matched)
        ln=matched[0];prior=int(ln.get('fixed_cycles',0));assert prior in (0,count),(ln['id'],prior,count)
        ln['fixed_cycles']=count;priced.append(dict(lane=ln['id'],bus=busname,old_fixed=prior,new_fixed=count))
    from tools.die_plan.gen import latency_table
    old_latency=raw.get('latency',{}).get('lanes',{})
    fresh=latency_table(S.Plan(raw,a.root/a.plan))
    latency_changes={lid:dict(old_cycles=old_latency.get(lid,{}).get('cycles'),new_cycles=row['cycles']) for lid,row in fresh.items() if old_latency.get(lid,{}).get('cycles')!=row['cycles']}
    raw['latency']={'lanes':fresh}
    payload_ff=sum(raw['ports'][next(i for i,p in enumerate(raw['ports']) if p['id']==oldlane['ports'][0])]['width']*oldlane['fixed_cycles'] for oldlane in raw['lanes'] if oldlane['id'] in {v['lane'] for v in priced})
    epoch_ff=sum(v['new_fixed'] for v in priced)
    report=dict(newly_realized_FF_vs_877=dict(payload=payload_ff,epoch=epoch_ff,total=payload_ff+epoch_ff),reference_transport_gate=dict(source_commit='3682e5dc88a0e39144775ff4bd86c18b10d7bb03',checks=320,valid_data_mismatches=0,epoch_mismatches=0,cfgfault_live_observations=251,mutant_catches=58,scope='Exact generated parent with real configuration and arithmetic/hash stubs; no full current-engine/G5 claim'),census_projection=changes,cfgfault_source_row=extra,public_ABI_corrections=abi,latency_changes=latency_changes,status='PLANNING candidate; no bind/STA/signoff adoption',pins=len(new),moved=moved,
        parent_data_census=rows,old_station_counts={v['conn']:len(v['regs_um']) for v in before},
        new_station_counts={v['conn']:len(v['regs_um']) for v in entries},
        cycle_delta=dict(core_RTL=0,parent_xtier_i0=1,parent_unit_i1=1,geometry_added_cycles=2,geometry_added_bit_cycles=329,historical_unpriced_PCI_cycles=2,historical_unpriced_RCO_cycles=1,word_stage_cycles_vs_raw_plan=5,parallel_RCO_valid_stage=1,sum_per_lane_fixed_cycles=6),priced_lanes=priced,
        wrapper_mapping='Exact877 generated parent: PCI264 identity; core RCO[1..38]→unit_o0[0..37], cfgfault→unit_o0[38], core RCO[0]→flt_o0[0]; FKS53 and VI_S276 identity. cfgfault soft-source placement requires actual parent trial.',
        remaining=['Materialize PCI2/RCOdata1/FKS1/VI_S1 plus parallel matching RCOvalid1 in bound RTL; lockstep/mutant and price actual causal graph. cfgfault must follow the same RCO word stage.',
                   'R5 engine core placement/route/signoff remains owned PATH-S81/head_eng; candidate LEF is not a signed view.'])
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(raw,separators=(',',':'))+'\n')
    a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
