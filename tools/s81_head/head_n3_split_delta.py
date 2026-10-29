#!/usr/bin/env python3
"""Separate independent N3 FT paths into disjoint strips, before landed compose.

This emits a RAW candidate: CA/START/clock infrastructure must be re-composed
for the new part identities. Station counts/data latency do not change.
"""
import argparse, copy, gzip, json
from pathlib import Path
from head_channel_resize_delta import crop_rect, shift_type, new_origin


def split(raw):
    p=copy.deepcopy(raw)
    # Infrastructure is derived from partition identities; invalidate it rather
    # than retaining a stale sidecar after the split.
    p['clock'].pop('landing_network',None)
    for t in p['partition_types'].values():
        for k in ('landing_contract','edge_clocks','reserved_sites_um','sink_sites_um'):
            t.get('clock',{}).pop(k,None)
        t.pop('count_straps',None)
    old=p['partition_types']['hd_st_n3']; w,h=old['outline_um']
    parts=[q for q in p['partitions'] if q['type']=='hd_st_n3']
    reports=[]; endpoint={}
    for group,names in [('transit',{'u2','d2'}),('turn',{'u1','d1'})]:
        tn='hd_st_n3_'+group
        t=copy.deepcopy(old)
        t['module']='ot_s81hd_st_n3_'+group
        t['ft_slots']=[f for f in t['ft_slots'] if f['name'] in names]
        total=sum(f['width']*f['stations'] for f in old['ft_slots'])
        weight=sum(f['width']*f['stations'] for f in t['ft_slots'])
        t['cells']=round(old.get('cells',0)*weight/total)
        t['note']=t.get('note','')+' | independent FT group split; proportional pre-synth cell estimate'
        rect=crop_rect(t)
        t,*_=shift_type(t,rect)
        p['partition_types'][tn]=t
        p['reset'].get('in_sites',{}).pop(tn,None)
        for q in parts:
            name=q['name']+'_'+group
            nq=copy.deepcopy(q);nq.update(name=name,type=tn,origin_um=new_origin(q['origin_um'],q.get('orient','R0'),w,h,rect))
            p['partitions'].append(nq)
            for slot in names:
                for suffix in ('_i','_o'):endpoint[(q['name'],slot+suffix)]=name
        reports.append({'type':tn,'crop_um':rect,'outline_um':t['outline_um'],
                        'stations':{f['name']:f['stations'] for f in t['ft_slots']}})
    for port in p['ports']:
        for side in ('src','dst'):
            end=port[side]; key=(end['part'],end['bus'])
            if key in endpoint:end['part']=endpoint[key]
    p['partitions']=[q for q in p['partitions'] if q['type']!='hd_st_n3']
    del p['partition_types']['hd_st_n3']
    p['reset'].get('in_sites',{}).pop('hd_st_n3',None)
    return p,{'status':'RAW_RECOMPOSE_REQUIRED','data_cycles_added':0,'parts_added':len(parts),'strips':reports,
              'required':['clock region membership for new parts','CA landing compose and sidecar','reset/START and die clock provider regeneration']}


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan');a.add_argument('--out',required=True);a.add_argument('--report',required=True);a=a.parse_args()
    op=gzip.open if a.plan.endswith('.gz') else open
    with op(a.plan,'rt') as f:p=json.load(f)
    p,r=split(p);Path(a.out).write_text(json.dumps(p,indent=1));Path(a.report).write_text(json.dumps(r,indent=1));print(json.dumps(r))
if __name__=='__main__':main()
