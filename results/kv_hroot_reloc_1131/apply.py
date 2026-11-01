#!/usr/bin/env python3
"""Prototype paired hroot landing relocation; zero RTL/cycle changes, canonical plan untouched."""
import argparse,copy,json,re,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import schema as S
HERE=Path(__file__).resolve().parent
FAN='i_seq__g_fan_N__u_fan_kc';SOUTH=['i_fch_pc_Q_N_q','i_kvpc_Q_N_pc__fo']

def shift_pin(pin,axis,delta):
    xy=pin.get('xy_um')
    if isinstance(xy,list):xy[axis]=round(xy[axis]+delta,6)

def shift_landing(t,bus,axis,delta):
    c=t['clock'];lc=c['landing_contract'];b=lc['bands'][bus]
    for k in [axis,axis+2]:b['rect_um'][k]=round(b['rect_um'][k]+delta,6)
    for p in lc['pins']:
        if p['name'] in ['fclk_in_'+bus,'cland_fstart_in_'+bus]:shift_pin(p,axis,delta)
    for e in c.get('edge_clocks',[]):
        if e['port']=='fclk_in_'+bus:e['tap_um'][axis]=round(e['tap_um'][axis]+delta,6)
    for e in lc.get('collector_local_sources',[]):
        if e['name']==bus:
            for k in ['xy_um','pin_xy_um']:
                if k in e:e[k][axis]=round(e[k][axis]+delta,6)
            e['band']=copy.deepcopy(b)

def nearest_tap(raw,tn,xy):
    P=S.Plan(raw,ROOT/'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json')
    taps=S.tap_grid(P,tn)
    return min(taps,key=lambda p:abs(p[1]-xy[0])+abs(p[2]-xy[1]))[0]

def apply(raw,variant):
    raw=copy.deepcopy(raw);sy,dx={'A':(144.384,172.8),'B':(142.656,181.44)}[variant]
    ts=raw['partition_types'];h=ts['kv3_hroot'];sites=h.setdefault('relay_sites',{})
    sites.update(json.load(open(HERE/'base_sites.json')))
    for x in json.load(open(HERE/('sites_'+variant+'.json'))):
        key=x['name'].removeprefix('u_bound.').split('$',1)[0].replace('\\','')
        old=sites.get(key,x['old']);sites[key]=[round(old[i]+x['new'][i]-x['old'][i],5) for i in range(2)]
    shift_landing(h,FAN,1,-sy)
    for bus in SOUTH:shift_landing(h,bus,0,dx)
    # E-face column must use existing y-pin-slot packing, not the N/S +x cursor.
    hb=h['clock']['landing_contract']['bands']['i_kvs_ctl_o_hroot_Q'];hb.pop('fill_axis',None)
    for e in h['clock']['landing_contract'].get('collector_local_sources',[]):
        if e['name']=='i_kvs_ctl_o_hroot_Q':e['band']=copy.deepcopy(hb)
    parts={p['name']:p for p in raw['partitions']};changed=[]
    for p in raw['ports']:
        if parts[p['dst']['part']]['type']!='kv3_hroot':continue
        bus=p['dst']['bus'];ori=parts[p['dst']['part']]['orient']
        if bus==FAN:delta=sy if ori in ('MX','R180') else -sy
        elif bus in SOUTH:delta=-dx if ori in ('MY','R180') else dx
        else:continue
        p['window_um']=[round(v+delta,6) for v in p['window_um']];changed.append(p['id'])
    # Source PC endpoint and its existing final interior relay move together.
    pc=ts['kv3_pc_v3'];ft=next(x for x in pc['ft_slots'] if x['name']=='ft1')
    # Existing seven-stage FT1 detours below/around the unchanged signed top cores.
    # Moving the old last station straight east would land inside kvpc3.
    for idx,x,ys,ref in [(2,863.298,[950.4,950.13],[864.0,950.4]),
                         (3,469.314,[950.13,950.4],[470.016,950.4]),
                         (4,72.738,[950.4,950.13],[73.44,950.4]),
                         (5,72.738,[1339.2,1338.93],[73.44,1339.2])]:
        for xy,y in zip(ft['bit_sites_um'][idx],ys):xy[:]=[x,y]
        ft['regs_um'][idx+1]=ref
    pc_tap=nearest_tap(raw,'kv3_pc_v3',[207.36 if variant=='A' else 216.0,1503.36])
    for p in pc['clock']['landing_contract']['pins']:
        for bus in ['ft1_o','o_kvpc_Q_N_pc__fo']:
            if p['name'] in ['fclk_out_'+bus,'cland_fstart_out_'+bus]:
                shift_pin(p,0,dx)
                if p['kind']=='clock':p['source_clock_tap']=pc_tap
    # Two mirrored hroot children share each hub: exports move apart symmetrically.
    for tn in ['kv3_hub_Wo','kv3_hub_Eo']:
        c=ts[tn]['clock'];x=17.28 if tn.endswith('Wo') else 1261.44
        for suffix,delta in [('',-sy),('_d1',sy)]:
            bus='o_seq__g_fan_N__u_fan_kc'+suffix
            fp=next(p for p in c['landing_contract']['pins'] if p['name']=='fclk_out_'+bus)
            y=fp['xy_um'][1]+delta;tap=nearest_tap(raw,tn,[x,y])
            for p in c['landing_contract']['pins']:
                if p['name'] in ['fclk_out_'+bus,'cland_fstart_out_'+bus]:
                    shift_pin(p,1,delta)
                    if p['kind']=='clock':p['source_clock_tap']=tap
    return raw,{'variant':variant,'fan_down_um':sy,'south_east_um':dx,'affected_types':['kv3_hroot','kv3_pc_v3','kv3_hub_Wo','kv3_hub_Eo'],'data_port_segments':changed,'added_cycles':0,'note':'Prototype only; existing register placement plus per-pin ring packing. Normal actual gates required.'}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('out');ap.add_argument('--variant',choices=['A','B'],required=True);a=ap.parse_args()
    p,receipt=apply(json.load(open(a.plan)),a.variant);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'plan.json').write_text(json.dumps(p,indent=1)+'\n');(out/'delta.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt))
