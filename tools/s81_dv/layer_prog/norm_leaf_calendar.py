#!/usr/bin/env python3
"""Derive leaf command spacing from actual emitted norm routes.

PDSK acts on returning native partials. Command spacing therefore includes both
physical boundary crossings as well as that deskew. Distinct command slots are
necessary because the XR receives one native control body per edge. A proposed
uniform PDSK is a plan-event candidate, never installed by this tool.
"""
import argparse
import itertools
import json
import re
from pathlib import Path


def calendars(report, depths=None):
    if report.get('schema')!='opentallas.s81.emitted_leaf_boundary_routes.v1' or report.get('verdict')!='PASS_SELECTED_BOUNDARY_WIRING':
        raise ValueError('actual emitted leaf boundary routes required')
    slices={}
    for row in report['leaves']:
        sl,k=row['slice'],row['leaf']
        identity=re.fullmatch(r'u_s_([0-7])([NS])',sl)
        if not identity or type(row['sid'])is not int or row['sid']!=2*int(identity[1])+(identity[2]=='N'):
            raise ValueError('actual slice SID identity differs')
        if type(k)is not int or not 0<=k<5 or k in slices.setdefault(sl,{}):
            raise ValueError('each actual slice needs five distinct leaf routes')
        for key in ('xr_command_to_leaf_boundary_edges','vn_b_partial_to_xr_input_edges','pdsk_edges'):
            if type(row[key])is not int or row[key]<0:raise ValueError('negative or noninteger source edge count')
        if row['crossing_plus_pdsk_edges']!=sum(row[key]for key in ('xr_command_to_leaf_boundary_edges','vn_b_partial_to_xr_input_edges','pdsk_edges')):
            raise ValueError('actual source edge sum differs')
        slices[sl][k]=row
    if len(slices)!=16 or any(set(rows)!=set(range(5))for rows in slices.values()):
        raise ValueError('complete actual16-slice80-leaf route cohort required')
    if depths is not None and (len(depths)!=5 or any(type(d)is not int or not 0<=d<8 for d in depths)):
        raise ValueError('one uniform five-entry3bit PDSK profile required')
    result={}
    for sl,rows in sorted(slices.items()):
        chosen=[rows[k]['pdsk_edges']for k in range(5)]if depths is None else list(depths)
        total=[rows[k]['xr_command_to_leaf_boundary_edges']+rows[k]['vn_b_partial_to_xr_input_edges']+chosen[k]for k in range(5)]
        # The unchanged native producer's common local latency cancels from
        # alignment. Do not import a legacy 115/117-edge producer constant.
        high=max(total);issue=[high-n for n in total]
        collisions=[dict(issue_offset=edge,leaves=[k for k,n in enumerate(issue)if n==edge])for edge in sorted(set(issue))if issue.count(edge)>1]
        result[sl]=dict(sid=rows[0]['sid'],pdsk=chosen,crossing_plus_pdsk_edges=total,
            command_offsets=issue,alignment_offset=high,command_span=max(issue),
            duplicate_command_slots=collisions,
            status='NECESSARY_SPACING_PASS'if not collisions else 'IMPOSSIBLE_ONE_COMMAND_PER_EDGE')
    return result


def diagnose(report):
    current=calendars(report)
    # This is the current source parameter's complete finite hardware domain,
    # not an arbitrary architecture/cycle search bound.
    bare={sl:[r['crossing_plus_pdsk_edges'][k]-r['pdsk'][k]for k in range(5)]for sl,r in current.items()}
    profiles=sorted(itertools.product(range(8),repeat=5),key=lambda ds:(max(ds),sum(ds),ds))
    selected=None
    for ds in profiles:
        if all(len({ages[k]+ds[k]for k in range(5)})==5 for ages in bare.values()):selected=ds;break
    out=dict(schema='opentallas.s81.norm_leaf_calendar.v1',
        status='SOURCE_RELATIVE_SPACING_ONLY',source_top_sha256=report['source_top_sha256'],
        source_view_sha256=report['source_view_sha256'],current=current,
        current_impossible_slices=[sl for sl,r in current.items()if r['duplicate_command_slots']],
        producer_local_latency='common local producer term cancels; no absolute output date inferred',
        scope='XR command input offsets and existing physical boundary/PDSK stages only',
        added_rtl_cycles=0,proposal_adopted=False,native_programme_qualified=False,full_token=False,
        holds=['plan-event approval and re-sign for any PDSK change','actual issuer-to-XR transport and global command slots',
               'measured native producer local age','NX injection/forward collisions and GO readiness',
               'RSTD/VQ release, retirement, HOST/reset/KS/START dates'])
    if selected is None:out['proposal']=None;return out
    proposal=calendars(report,selected)
    for sl,row in proposal.items():
        old=current[sl];anchor=max(old['alignment_offset'],row['alignment_offset'])
        offsets=[anchor-n for n in row['crossing_plus_pdsk_edges']]
        row.update(preserved_or_advanced_cohort_anchor=anchor,
            added_cohort_output_edges=anchor-old['alignment_offset'],
            command_offsets_at_cohort_anchor=offsets,
            command_shift_from_old_necessary_offsets=[offsets[k]-old['command_offsets'][k]for k in range(5)])
    out['proposal']=dict(pdsk=list(selected),parameter_value=sum(n<<(3*k)for k,n in enumerate(selected)),
        selection='minimum maximum depth, then minimum total depth, then lexicographic profile over complete3bit domain',
        calendars=proposal,leaf_stage_delta={sl:[selected[k]-r['pdsk'][k]for k in range(5)]for sl,r in current.items()},
        maximum_command_span=max(r['command_span']for r in proposal.values()),
        maximum_added_cohort_output_edges=max(r['added_cohort_output_edges']for r in proposal.values()),
        logical_partial_pipeline_bit_delta_per_master={sl:33*(sum(selected)-sum(r['pdsk']))for sl,r in current.items()},
        qualification='necessary per-slice spacing only; global schedule and parameter adoption unqualified')
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('routes',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('preserve prior diagnosis; choose a fresh output')
    result=diagnose(json.loads(a.routes.read_text()));a.out.write_text(json.dumps(result,indent=1)+'\n')
    print('NORM_LEAF_CALENDAR',len(result['current_impossible_slices']),'current impossible slices; proposal',result['proposal']['pdsk']if result['proposal']else None)
