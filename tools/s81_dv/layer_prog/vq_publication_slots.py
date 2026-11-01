#!/usr/bin/env python3
"""Predict local VQ fragment slots from current source-only boundary stages.

A common VN/VQ local latency cancels between a slice's five leaves. Physical
clock phases and global V/ring routing remain outside this prediction.
"""
import argparse
from collections import defaultdict
import itertools
import json
from pathlib import Path


def analyze(vq,rstd):
    if vq.get('status')!='PASS_CURRENT_VQ_SOURCE_AND_BOUNDARY_WIRING' or rstd.get('status')!='PASS_CURRENT_RSTD_BOUNDARY_WIRING' or vq['source_top_sha256']!=rstd['source_top_sha256']:
        raise ValueError('matching current source VQ and RSTD boundaries required')
    back={(r['slice'],r['leaf']):r for r in rstd['leaves']}
    if len(back)!=80 or len(rstd['leaves'])!=80 or len(vq['records'])!=80:raise ValueError('actual80-leaf cohort required')
    groups={}
    for r in vq['records']:
        sl,k=r['slice'],r['leaf'];key=(sl,k)
        if key not in back or r['global_beat']!=5*r['sid']+k:raise ValueError('current VQ/RSTD ownership differs')
        age=back[key]['XR_RSTD_output_to_VN_RSTD_input_edges']+r['VN_to_VQ_stream_edges']+r['VQ_output_to_XG_input_edges']
        groups.setdefault(sl,[]).append(dict(leaf=k,sid=r['sid'],source_stage_offset=age,k=r['selected_vq_k']))
    if len(groups)!=16 or any(sorted(r['leaf']for r in rows)!=list(range(5))for rows in groups.values()):raise ValueError('actual16distinct5-leaf slices required')
    def slots(rows,profile=None,both=False):
        occupied=defaultdict(list)
        for row in rows:
            k=row['k']if profile is None else profile[row['leaf']]
            for family in ([0,20]if both else[0]):
                for fragment in range(4):occupied[row['source_stage_offset']+4*k+family+fragment].append((row['leaf'],family,fragment))
        return {str(edge):values for edge,values in sorted(occupied.items())if len(values)>1}
    profiles=list(itertools.permutations(range(5)))
    candidates=[p for p in profiles if all(not slots(rows,p)for rows in groups.values())]
    both=[p for p in profiles if all(not slots(rows,p,True)for rows in groups.values())]
    current={sl:dict(leaves=rows,overlap_edges=slots(rows))for sl,rows in sorted(groups.items())}
    return dict(schema='opentallas.s81.current_VQ_local_fragment_slots.v1',status='PREDICTED_SOURCE_STAGE_SLOTS_ONLY',
        source_top_sha256=vq['source_top_sha256'],current=current,
        current_slices_with_overlaps=[sl for sl,row in current.items()if row['overlap_edges']],
        legal_uniform_profiles_tested=len(profiles),single_family_uniform_candidates=[list(p)for p in candidates],
        both_families_uniform_candidates=[list(p)for p in both],candidate_adopted=False,
        common_local_latency=None,physical_phases_qualified=False,full_token=False,
        source_semantics='VQ k_c is used only by xf_v/xf_s timing comparators; header gidx is runtime mi from m_i, independent of k',
        holds=['actual same-data VQ transaction check and actual rstop capture','complete global V/ring/XQ/BF16 routing and clock phases',
               'coordinator-approved strap/plan event before any K change'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--vq',type=Path,required=True);p.add_argument('--rstd',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('preserve previous prediction; choose a fresh output')
    r=analyze(json.loads(a.vq.read_text()),json.loads(a.rstd.read_text()));a.out.write_text(json.dumps(r,indent=1)+'\n')
    print('VQ_LOCAL_SLOTS source-overlap slices',len(r['current_slices_with_overlaps']),'single-family candidates',r['single_family_uniform_candidates'],'both-family candidates',len(r['both_families_uniform_candidates']))
