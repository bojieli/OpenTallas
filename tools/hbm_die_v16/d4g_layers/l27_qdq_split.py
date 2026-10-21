#!/usr/bin/env python3
"""Expand hb_quant_NW into the actual CLOSED QDQ r3 leaf instances.

Netmap is produced by qdq_split_netmap.py on the fleet from the existing RTL.
The controller's RL/WC straps are set again by l12 from the actual bank/relay budget.
The parent remains in split_parents solely as a range map, never as a placed cell.
"""
import argparse, collections, copy, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/hbm_die_v15'))
import full_die_v16 as F
from soft_parent import soft_flatten
PARENT='hb_quant_NW'
REGION='d4g_l27_qdq_split'

def apply(original,nm):
    c=copy.deepcopy(original);I=c['instances'];p=I[PARENT]
    if p['master'] not in ('ot_hgi_qdq_host_split','ot_hgi_qdq_host_split_r2'):
        raise ValueError('QDQ split requires the old host composition')
    # Functional ports are unchanged; the physical root ABI is now one decoder and four LG roots.
    for old in ('clk_dxl','clk_dbq','clk_daq'):p['ports'].pop(old)
    p['ports']['clk_dec']=dict(direction='input',bits=1)
    p['ports']['clk_lg']=dict(direction='input',bits=4)
    p['master']=nm['top'];p['source']='rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_host_split_r3.sv';p['params']=dict(nm['params'])
    clocks=[];dec=None;lg=None
    for x in c['clock_resets']:
        if x['instance']==PARENT and x['port'] in ('clk_dxl','clk_dbq','clk_daq'):
            if x['port']=='clk_dxl':dec=dict(x,port='clk_dec')
            continue
        clocks.append(x)
        if x['instance']==PARENT and x['port']=='clk_transport':lg=dict(x,port='clk_lg',bits=4)
    if dec is None or lg is None:raise ValueError('QDQ decoder/transport clock roots missing')
    clocks.extend([dec,lg]);c['clock_resets']=clocks
    ports={n:x['ports'] for n,x in I.items()};drv={}
    for e in c['edges']:
        si,sp,lo,hi=e['source'];di,dp,dl,dh=e['sink']
        for b in range(hi-lo):drv[(di,dp,dl+b)]=(si,sp,lo+b)
    slots={}
    for cn,x in nm['children'].items():
        rp=x['rtl_path']
        if rp=='program_leaf':s='quant_NW_prog'
        elif rp=='u_dec':s='quant_NW_dec'
        elif rp.endswith('.ctl'):s='quant_NW_xp_ctl'
        elif '.rslice' in rp:s='quant_NW_xp_rslice'+rp.split('[')[1].split(']')[0]
        elif '.wslice' in rp:s='quant_NW_xp_wslice'+rp.split('[')[1].split(']')[0]
        elif rp.endswith('.lg'):s=rp.split('.')[0]+'_lg'
        else:s='quant_NW_glue_'+str(len(slots))
        slots[cn]=s
    problems=[]
    split=soft_flatten(PARENT,nm,I,ports,drv,c['edges'],c['clock_resets'],c['straps'],F.Rtl(),problems,slots=slots)
    if problems:raise ValueError(problems)
    children={};ctl=None;lgs=[]
    for cn,x in nm['children'].items():
        n=PARENT+'__'+cn;v=I[n];v['region']=REGION;v['split_of']=PARENT
        v['note']=f'QDQ r3 actual soft-parent child {x["rtl_path"]}; zero hidden parent logic'
        if x['physical_view']:v['physical_view']=x['physical_view']
        if x['master']=='ot_hgi_qdq_transport_ctl_r4':
            ctl=n;v['closed_record']='5b80fa332'
        if x['master']=='ot_hgi_qdq_lg_port_group_r2':
            lgs.append(n);v['latency_budget']={'RL':nm['params']['RL']}
        children[n]=dict(master=x['master'],slot=v['slot'],physical_view=v.get('physical_view'))
    # Full per-bit map preserves sliced bank-pair offsets in path consumers.
    ranges={}
    for p,pd in split['_parent_ports'].items():
        ranges[p]=[split['_map_range'](p,b,b+1) for b in range(pd['bits'])]
    c.setdefault('split_parents',{})[PARENT]=dict(master=nm['top'],children=split['children'],port_bits=ranges,
        ports={p:sorted({(r[0],r[1]) for bits in refs for r in bits}) for p,refs in ranges.items()})
    # Gap ranges are real parent-port ranges and must follow the same bit map.
    for gap in c.get('gaps',[]):
        for field in ('unconnected_inputs','unconsumed_outputs'):
            if field not in gap:continue
            refs=[]
            for ref in gap[field]:
                if ref[0]!=PARENT:refs.append(ref);continue
                refs.extend(split['_map_range'](ref[1],ref[2],ref[3]))
            gap[field]=refs
    c['qdq_split']=dict(parent=PARENT,ctl=ctl,lgs=sorted(lgs),RL=nm['params']['RL'],WC=nm['params']['WC'],XR=nm['params']['XR'],
        timing=dict(nm['timing']),clock_boundary='program_leaf to ctl: parent compensation ~82ps or priced fixed-latency landing required',
        records=['41f53364b','5b80fa332'],netmap_sources=nm['sources'])
    for e in c['edges']:
        if e.get('region')=='idx_soft' and e['source'][0].startswith(PARENT+'__') and e['sink'][0].startswith(PARENT+'__'):e['region']=REGION;e['clock']='stream'
    c.setdefault('summary',{}).update(instances=len(I),edges=len(c['edges']),edge_bits=sum(e['bits'] for e in c['edges']))
    return c,dict(layer=REGION,children=children,physical_children=nm['physical_children'],glue_cells=nm['glue_cells'],
        timing=c['qdq_split']['timing'],remaining_parent_holds=['actual station-priced XR/RTL straps via l12','~82ps program/ctl parent compensation or landed command crossing','new leaf slots and final die physical closure'])



def bind_grants(original,c):
    """Use the existing QUANT reservations; expose exact native outlines at die coordinates.

    Existing nested origins were passed through the die coordinate cut map, so
    rebuilding these local offsets also avoids applying those cuts twice.
    The existing plan/GRT pass owns overlap/reach legality, as for all new grants.
    """
    import re
    g=copy.deepcopy(original);slots={s['name']:s for s in g['slots']}
    xp=slots['quant_NW_xp'];xp0=xp['origin'];old=slots['hb_quant_NW'];old0=old['origin']
    positions={
        'quant_NW_prog':(old0['x']+9.612,old0['y']+55.08),
        'quant_NW_dec':(slots['quant_NW_dec']['origin']['x']+154.72,slots['quant_NW_dec']['origin']['y']),
        'quant_NW_xp_ctl':(xp0['x']+21.6,xp0['y']+21.6)}
    for k in range(4):
        root=slots[f'quant_NW{k}']['origin']
        positions[f'quant_NW{k}_lg']=(root['x']+39.8,root['y']+25.3)
        positions[f'quant_NW_xp_rslice{k}']=(xp0['x']+172.8+151.2*k,xp0['y']+21.6)
        positions[f'quant_NW_xp_wslice{k}']=(xp0['x']+172.8+151.2*k,xp0['y']+129.6)
    gi=0
    for n in c['split_parents'][PARENT]['children']:
        x=c['instances'][n];slot=x['slot'];view=x.get('physical_view')
        if view:
            lef=ROOT/view/(x['master']+'.lef')
            wh=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef.read_text())
            if not wh:raise ValueError('native LEF has no outline '+str(lef))
            w,h=map(float,wh.groups());px,py=positions[slot]
        else:
            w=h=24.;px=old0['x']+9.612+gi*43.2;py=old0['y']+9.6;gi+=1
        s=copy.deepcopy(slots.get(slot,old));s.update(name=slot,instance=n,cell=x['master'],kind='tile',parent='die',
            source=x['source'],params=x['params'],outline=dict(w=w,h=h),origin=dict(x=px,y=py,orient='R0'),
            grant=REGION,pins=[],pin_status='ACTUAL_VIEW' if view else 'SOURCE_SYNTH',
            notes='QDQ r3 consumed actual child; outline from closed LEF' if view else 'QDQ r3 actual one-bit combinational glue; synthesis owns final cell size')
        if view:s['physical_view']=view
        if slot in slots:slots[slot].clear();slots[slot].update(s)
        else:g['slots'].append(s);slots[slot]=s
    g['slots']=[s for s in g['slots'] if s['name']!='hb_quant_NW']
    return g


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('inp');a.add_argument('netmap');a.add_argument('out');a.add_argument('--report',required=True);a.add_argument('--grants');a.add_argument('--out-grants');x=a.parse_args()
    c,r=apply(json.load(open(x.inp)),json.load(open(x.netmap)))
    if x.grants:
        if not x.out_grants:a.error('--grants requires --out-grants')
        g=bind_grants(json.load(open(x.grants)),c);Path(x.out_grants).write_text(json.dumps(g,indent=1)+'\n')
        r['grant_slots_bound']=len(c['split_parents'][PARENT]['children'])
    Path(x.out).write_text(json.dumps(c,separators=(',',':'))+'\n');Path(x.report).write_text(json.dumps(r,indent=1)+'\n')
