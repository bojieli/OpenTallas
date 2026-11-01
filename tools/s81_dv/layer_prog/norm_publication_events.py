#!/usr/bin/env python3
"""Compose source-relative normalization publication dates from native receipts.

The common upstream partial-production term remains explicit and unknown. This
emits neither a HOST job nor START authority or a qualified physical calendar.
"""
import argparse,json
from pathlib import Path


def compose(book,network,slots,native):
    if network.get('status')!='PASS_CURRENT_NX_COMPONENT_NETWORK' or network['source_top_sha256']!=slots['source_top_sha256'] or book['source_top_sha256']!=slots['source_top_sha256']:
        raise ValueError('matching selected source book, NX component and VQ source required')
    if book.get('native_job_sealed')is not False or book['families']not in (1,2,3):
        raise ValueError('explicit unsealed norm book required')
    if native.get('status')!='PASS_CURRENT_NATIVE_PUBLICATION_COMPONENT' or native['source_top_sha256']!=slots['source_top_sha256']:raise ValueError('matching current native publication receipt required')
    # Current actual flattened s_0S_L0 native RSTD→VQ first Q is46, BF66,
    # native_leaf_ece_v5; all80 selected VN→VQ source stages are0.
    events=[];profiles=slots['both_families_per_slice_k0to4']
    for sl,group in slots['current'].items():
        for row in group['leaves']:
            sid,leaf=row['sid'],row['leaf'];rstd=network['actual_RSTD'][str(sid)][0]
            k=profiles[sl]['profile'][leaf]
            for family,mask,age in [('q',1,native['Q_first_fragment_edges']),('bf16',2,native['BF16_first_fragment_edges'])]:
                if not book['families']&mask:continue
                first=rstd+2+row['source_stage_offset']+age+4*k
                for fragment in range(4):
                    events.append(dict(slice=sl,sid=sid,leaf=leaf,global_beat=5*sid+leaf,
                        header_index=book['head_egress_flag']+5*sid+leaf,family=family,
                        fragment=fragment,candidate_k=k,relative_XG_input_edge=first+fragment))
    return dict(schema='opentallas.s81.norm_publication_source_events.v1',
        status='UNSEALED_SOURCE_RELATIVE_COMPONENT_CALENDAR',events=events,
        source_top_sha256=slots['source_top_sha256'],consumer=book['consumer'],
        source_XFIN_RSTD_to_XRT_input_edges=0,source_XRT_RSTD_input_to_output_edges=2,
        source_native_Q_age=native['Q_first_fragment_edges'],source_native_BF16_age=native['BF16_first_fragment_edges'],
        common_upstream_partial_producer_edges=None,
        component_epoch=network['component_epoch'],
        last_relative_fragment_edge=max(e['relative_XG_input_edge']for e in events),
        native_age_directly_tested_part=native['native_part'],all80_native_phases_qualified=False,
        source_configuration_adopted=False,global_allgather_qualified=False,
        final_POST_residency_qualified=False,HOST_START_authority=False,full_token=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('book','network','slots','native','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('choose fresh event output')
    result=compose(*[json.loads(getattr(a,n).read_text())for n in ('book','network','slots','native')])
    a.out.write_text(json.dumps(result,indent=1)+'\n');print(result['status'],len(result['events']),'fragments',result['last_relative_fragment_edge'])
