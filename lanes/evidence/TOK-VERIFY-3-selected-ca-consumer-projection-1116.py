#!/usr/bin/env python3
"""Project selected CA schedule changes onto existing KV consumer members.

Old padding is held fixed solely to expose pressure on R8 and programme ages.
The output is never a replacement bus_groups file or a qualified programme.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from functools import lru_cache


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def project(old_path, candidate_path, groups_path, latency_path):
    old=json.loads(old_path.read_bytes());new=json.loads(candidate_path.read_bytes())
    a,b=old['count_aligned'],new['count_aligned']
    if set(a['ports'])!=set(b['ports']):raise ValueError('candidate changes selected DATA port universe')
    old_rows={r['port']:r for r in old['ports']};new_rows={r['port']:r for r in new['ports']}
    delta={};lane=defaultdict(int)
    for pid,c in a['ports'].items():
        x,y=old_rows[pid],new_rows[pid]
        if any(x[k]!=y[k] for k in ['lane','src','dst','width']):raise ValueError('candidate changes physical DATA endpoint/lane '+pid)
        if c['depth']!=b['ports'][pid]['depth'] or c.get('freg',0)!=b['ports'][pid].get('freg',0):
            raise ValueError('candidate changes depth/FREG hardware '+pid)
        d=int(b['ports'][pid]['sched_lat'])-int(c['sched_lat'])
        delta[pid]=d;lane[x['lane']]+=d
    latency=json.loads(latency_path.read_bytes())
    buses={r['lane']:r for r in latency['buses']if r['lane'] is not None}
    if len(buses)!=sum(r['lane']is not None for r in latency['buses']):raise ValueError('duplicate logical lane')
    @lru_cache(None)
    def trace(lid, bit):
        it=buses[lid]['source_bits'][bit]
        if it[0]=='leaf':return (it[1]+'.'+it[2],int(it[3]),lane.get(lid,0))
        if it[0]!='forward':raise ValueError('unknown source kind')
        source,origin,d=trace(it[1],int(it[2]))
        return source,origin,d+lane.get(lid,0)
    @lru_cache(None)
    def origins(lid):
        found={}
        for i in range(len(buses[lid]['source_bits'])):
            source,origin,d=trace(lid,i)
            if (source,origin)in found and found[source,origin]!=d:raise ValueError('ambiguous source path')
            found[source,origin]=d
        return found
    def member_delta(m):
        if m['lane']=='spine':return 0 # raw reset spine is outside selected DATA CA contract
        source_map=origins(m['lane'])
        ds={source_map[m['source'],i]for lo,hi in m['source_bits']for i in range(lo,hi+1)}
        if len(ds)!=1:raise ValueError('candidate splits a current source member '+repr((m,ds)))
        return next(iter(ds))
    groups=json.loads(groups_path.read_bytes())
    changed=[];lose_alignment=[];old_target_exceeded=[]
    before=defaultdict(set);after=defaultdict(set)
    for g in groups['landing']:
        old_offsets=set();new_offsets=set()
        for m in g['members']:
            d=member_delta(m)
            old_offsets.add(m['landed_stages']-m['asbuilt_stages'])
            new_offsets.add(m['landed_stages']+d-m['asbuilt_stages'])
            key=(g['sink'],m['sink_port'])
            before[key].add(m['landed_stages']);after[key].add(m['landed_stages']+d)
            if d:
                record=dict(sink=g['sink'],sink_port=m['sink_port'],source=m['source'],lane=m['lane'],
                            delta=d,old_bound=m['bound_stages'],old_landed=m['landed_stages'],
                            old_pad=m['landed_stages']-m['bound_stages'],
                            projected_raw_bound=m['bound_stages']+d,
                            projected_landed_old_pad=m['landed_stages']+d)
                changed.append(record)
                if record['projected_raw_bound']>record['old_landed']:old_target_exceeded.append(record)
        if len(old_offsets)==1 and len(new_offsets)>1:
            lose_alignment.append(dict(sink=g['sink'],src_part=g['src_part'],
                                       old_offsets=sorted(old_offsets),projected_offsets=sorted(new_offsets)))
    names=[('kvs_attn','d2d__srx'),('kvs_attn','d2d__rx_payload'),('kvs_attn','d2d__att_tx_slot'),
           ('kvs_attn','d2d__att_tx_kind'),('kvs_attn','d2d__att_tx_beat'),('d2d_kv','att_tx_v'),('d2d_kv','att_tx_payload')]
    seam={'.'.join(k):dict(old=sorted(before[k]),projected_old_padding=sorted(after[k]))for k in names}
    def rt(category):
        out_old=set();back_old=set();out_new=set();back_new=set()
        for g in groups['landing']:
            for m in g['members']:
                d=member_delta(m);src=m['source'];port=m['sink_port'];direction=None
                if category=='host':
                    if src.startswith('d2d_kv.record_') and src.split('.',1)[1]==port:direction='out'
                    elif g['sink']=='d2d_kv'and port in ['record_tx_observed_v','record_tx']:direction='back'
                else:
                    if src=='d2d_kv.emb_tx_slot'and g['sink']=='kvs_emb':direction='out'
                    elif g['sink']=='d2d_kv'and port in ['emb_tx_v','emb_tx_payload']:direction='back'
                if direction=='out':out_old.add(m['landed_stages']);out_new.add(m['landed_stages']+d)
                if direction=='back':back_old.add(m['landed_stages']);back_new.add(m['landed_stages']+d)
        scalar=lambda x,y:sum([next(iter(x))if x else 0,next(iter(y))if y else 0])if len(x)<=1 and len(y)<=1 else None
        return dict(old_out=sorted(out_old),old_back=sorted(back_old),old_round_trip=scalar(out_old,back_old),
                    projected_out_old_padding=sorted(out_new),projected_back_old_padding=sorted(back_new),
                    projected_round_trip_old_padding=scalar(out_new,back_new))
    return dict(schema='opentallas.kv.selected-ca-consumer-projection.v1',
                status='UNADOPTED_RAW_CA_PROJECTION_R8_REBIND_REQUIRED',
                route_method='per-bit recursive forwarding from native bind_latency source_bits; every current member required uniform delta',
                inputs={str(p):sha(p)for p in [old_path,candidate_path,groups_path,latency_path]},
                same_selected_data_ports=len(delta),new_data_rings=0,depth_FREG_preserved=True,
                crossing_delta_hist=dict(sorted(Counter(delta.values()).items())),
                aggregate_crossing_cycle_delta=sum(delta.values()),
                lane_delta_hist=dict(sorted(Counter(lane.values()).items())),
                changed_lanes={k:v for k,v in lane.items()if v},
                changed_bus_group_members=len(changed),
                previously_aligned_groups_now_skewed_old_padding=len(lose_alignment),
                previously_aligned_group_examples=lose_alignment[:20],
                old_landed_target_below_new_raw_bound_members=len(old_target_exceeded),
                old_target_examples=old_target_exceeded[:20],
                seam_KST_members=seam,host=rt('host'),embedding=rt('embedding'),
                changed_member_examples=changed[:30],
                limits=['Old padding held fixed is an analytical projection, not a new bound contract.',
                        'bind.align_r8 pins raw bound depth; any changed member invalidates an old matching R8 table even where more/less padding could preserve final age.',
                        'Do not sum crossing/lane cycle changes as per-token latency or publish a token-rate delta.',
                        'Physical START stage build/route and coherent strict bind/LATCHECK/R8/new ages/current source programme remain required.'],
                programme_written=False,actual_rate_delta=None,physical_adoption=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ['old','candidate','groups','latency','out']:ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists():raise ValueError('existing projection never overwritten')
    r=project(a.old,a.candidate,a.groups,a.latency)
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(r['status'],r['crossing_delta_hist'],r['changed_bus_group_members'],r['previously_aligned_groups_now_skewed_old_padding'])


if __name__=='__main__':main()
