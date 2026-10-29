#!/usr/bin/env python3
"""Static HEAD NORMR booking from exact command/partial transport ages.

The current controller has one command body per cycle. A delay profile is
bookable only when all five required issue offsets are distinct. Candidate
PDSK changes are outputs for die-owner review, never applied to a plan/RTL.
The caller supplies a relative VO origin and EPS; physical START is unknown.
"""
import argparse
import itertools
import json
from pathlib import Path


def literal(value):
    if type(value) is int:return value
    if not isinstance(value,str):raise ValueError('exact integer source parameter required')
    if "'" not in value:return int(value,10)
    width,word=value.split("'",1);radix={'b':2,'d':10,'h':16,'o':8}[word[0].lower()]
    number=int(word[1:].replace('_',''),radix)
    if not 0<=number<1<<int(width):raise ValueError('source parameter exceeds width')
    return number


def profile(value):return [(literal(value)>>(3*k))&7 for k in range(5)]
def encoded(delays):
    if len(delays)!=5 or any(type(x)is not int or not 0<=x<=7 for x in delays):raise ValueError('five3bit delays required')
    return sum(d<<(3*k)for k,d in enumerate(delays))


def offsets(extra,delays):
    effective=[a+b for a,b in zip(extra,delays)]
    if len(set(effective))!=5:return None
    target=max(effective)
    return [target-a for a in effective]


def select_profile(extras):
    # One common profile, bounded by the EXISTING five3bit fields. Fewer
    # storage stages first; no extra controller type or widened interface.
    candidates=sorted(itertools.product(range(8),repeat=5),key=lambda p:(sum(p),max(p),p))
    for candidate in candidates:
        if all(offsets(extra,candidate)is not None for extra in extras):return list(candidate)
    raise ValueError('no existing-width common static delay profile is bookable')


def compile_booking(entry,returns,network,control,base_edge,eps_bits,choose=False,interleave=False):
    hashes=[(d.get('source_asbuilt_sha256'),d.get('die_sha256'))for d in(entry,returns,network,control)]
    if len(set(hashes))!=1:raise ValueError('all inputs must use one exact source/bound graph')
    if type(base_edge)is not int or base_edge<0 or type(eps_bits)is not int or not 0<=eps_bits<1<<32:
        raise ValueError('explicit relative origin and binary32EPS required')
    ent={(x['slice'],x['leaf']):x for x in entry['leaves']}
    ret={(x['slice'],x['leaf']):x for x in returns['leaves']}
    sid={r['slice']:r['sid']for r in network['transport']['nx_boundary']}
    info={r['slice']:r for r in network['xr_xfin']}
    if len(sid)!=16 or set(sid.values())!=set(range(16)):raise ValueError('all16source slice IDs required')
    extras={}
    existing={}
    for sl in sid:
        existing[sl]=profile(info[sl]['xr_params']['PDSK'])
        if any(ent[(sl,k)]['status']!='PASS' or ret[(sl,k)]['status']!='PASS'for k in range(5)):
            raise ValueError('unqualified source command/return route')
        extras[sl]=[ent[(sl,k)]['command_transport_edges']+ret[(sl,k)]['partial_return_edges']for k in range(5)]
    if any(x!=next(iter(existing.values()))for x in existing.values()):raise ValueError('current source does not use one common PDSK profile')
    old=next(iter(existing.values()));new=select_profile(list(extras.values()))if choose else old
    collisions=[]
    for sl,extra in extras.items():
        effective=[x+y for x,y in zip(extra,old)]
        repeated=sorted({x for x in effective if effective.count(x)>1})
        if repeated:collisions.append(dict(slice=sl,effective_offsets=effective,duplicates=repeated))
    rows=[];groups=[];old_last=base_edge+20+8*6-1
    for tier in ('N','S'):
        slices=sorted((s for s in sid if s.endswith(tier)),key=sid.get)
        mask=sum(1<<sid[s]for s in slices)
        rows.append(dict(engine='V'+tier,issue_vo_edge=base_edge,slice_mask=mask,target=0,leaf_mask=31,body=1|(480<<4),kind='GAIN'))
        next_issue=base_edge+20
        occupied={base_edge}
        for sl in slices:
            issue=offsets(extras[sl],new)
            if issue is None:raise ValueError(f'{sl}: onebodycommand/cycle cannot realize profile {new}; equal issue offsets')
            start=base_edge+20 if interleave else next_issue
            booked=issue+[max(issue)+1]
            while any(start+off in occupied for off in booked):start+=1
            occupied.update(start+off for off in booked)
            ctl=control['paths'][sl]
            if ctl['status']!='PASS':raise ValueError('current controller source timing missing')
            for k,off in enumerate(issue):
                index=128+5*sid[sl]+k
                body=7|(1008<<4)|(index<<14)|(2<<24)
                rows.append(dict(engine='V'+tier,issue_vo_edge=start+off,slice_mask=1<<sid[sl],target=0,leaf_mask=1<<k,
                    body=body,kind='NORMR',slice=sl,leaf=k,
                    xr_command_pin_edge=start+off+ctl['xr_command_pin_edge'],
                    vp_command_pin_edge=start+off+ctl['xr_command_pin_edge']+ent[(sl,k)]['command_transport_edges']))
            finish=start+max(issue)+1
            rows.append(dict(engine='V'+tier,issue_vo_edge=finish,slice_mask=1<<sid[sl],target=1,leaf_mask=0,body=eps_bits,kind='XFIN_GO',slice=sl))
            groups.append(dict(slice=sl,sid=sid[sl],extra_command_return_edges=extras[sl],old_delays=old,
                proposed_delays=new,normr_issue_offsets=issue,start_vo_edge=start,last_vo_edge=finish,
                aligned_partial_edge_excluding_common_local_vp_latency=start+ctl['xr_command_pin_edge']+max(a+b for a,b in zip(extras[sl],new))))
            next_issue=finish+1
    used=set()
    for row in rows:
        key=(row['engine'],row['issue_vo_edge'])
        if key in used:raise ValueError('unsupported multiissue '+str(key))
        used.add(key)
        row['ctl_payload']=row['slice_mask']|(row['target']<<16)|(row['leaf_mask']<<21)|(row['body']<<26)
    rows.sort(key=lambda r:(r['issue_vo_edge'],r['engine']))
    return dict(schema='opentallas.head.norm_booking.v1',scope='CANDIDATE_RELATIVE_HEAD_NORM_PROGRAMME',
        source_asbuilt_sha256=hashes[0][0],die_sha256=hashes[0][1],base_vo_edge=base_edge,eps_bits=eps_bits,
        pdsk_current=old,pdsk_candidate=new,pdsk_parameter=f"15'd{encoded(new)}",changed_signed_contract=old!=new,
        adoption=False,die_owner_approval_required=old!=new,old_profile_issue_collisions=collisions,
        rows=rows,groups=groups,commands=len(rows),unsupported_multiissue=False,
        old_consecutive_programme_last_vo_edge=old_last,new_last_vo_edge=max(r['issue_vo_edge']for r in rows),
        added_control_span_edges=max(r['issue_vo_edge']for r in rows)-old_last,
        interleaved_groups=interleave,
        local_normr_to_partial_edges=None,actual_producer_outputs_qualified=False,absolute_START_qualified=False,full_token=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in('entry','returns','network','control','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--base-edge',type=int,required=True);p.add_argument('--eps-bits',type=lambda s:int(s,0),required=True)
    p.add_argument('--candidate-profile',action='store_true');p.add_argument('--interleave-groups',action='store_true');a=p.parse_args()
    if a.out.exists():raise ValueError('preserve previous booking')
    result=compile_booking(*[json.loads(getattr(a,k).read_text())for k in('entry','returns','network','control')],
        a.base_edge,a.eps_bits,a.candidate_profile,a.interleave_groups)
    a.out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:result[k]for k in('pdsk_current','pdsk_candidate','commands','added_control_span_edges','adoption')}))
