#!/usr/bin/env python3
"""Export literal canonical FIELD stages separately from SU execution homes.

HE/CROM provider placement is deliberately not interpreted as an SU home.
Missing actual instances, programs, native kernels or boundary calendars are
reported per stage/rank and cannot qualify executable activity.
"""
import collections

REQUIRED=('su_instance','vm_instance','su_source_sha256','vm_source_sha256',
          'program_sha256','operand_allocation_sha256','memory_image_sha256',
          'core_epoch','duration_edges','boundary_activity','native_kernel_bindings')

def export(stages, fragments, nodes, bindings=()):
    if len(stages['PHW_required_by_stage']) != 81:
        raise ValueError('canonical81 stages required')
    dies={}
    for die in stages['rank_dies']:
        key=(die['stage'],die['rank'])
        if key in dies or key[0] not in range(81) or key[1] not in range(4):
            raise ValueError('canonical stage/rank duplicate or range')
        dies[key]=die['die_id']
    if len(dies)!=324 or len(set(dies.values()))!=324:
        raise ValueError('canonical324 physical rank dies required')
    actual={}
    for b in bindings:
        key=(b['stage'],b['rank'])
        if key not in dies or key in actual or b['die_id']!=dies[key]:
            raise ValueError('actual SU instance must bind unique canonical rank die')
        if 'provider_home' in b:
            raise ValueError('HE/CROM provider home cannot supply SU execution home')
        actual[key]=b
    bystage=collections.defaultdict(list)
    for f in fragments:
        if f['stage'] not in range(81):raise ValueError('fragment stage')
        bystage[f['stage']].append(f)
    records=[]
    for stage in range(81):
        fs=bystage[stage]
        for rank in range(4):
            b=actual.get((stage,rank),{})
            missing=[k for k in REQUIRED if b.get(k) is None]
            # An empty activity/kernel list is not evidence of a valid no-op.
            if b and (not b.get('boundary_activity') or not b.get('native_kernel_bindings')):
                missing.append('nonempty_source_bound_execution_or_explicit_noop_proof')
            if b and (type(b.get('duration_edges')) is not int or b.get('duration_edges',0)<=0):
                missing.append('positive_compiled_duration')
            records.append(dict(stage=stage,rank=rank,die_id=dies[(stage,rank)],
                PHW=stages['PHW_required_by_stage'][stage],
                field_fragment_count=len(fs),source_layers=sorted({f['layer'] for f in fs},key=str),
                field_rank_scalar_rows=sum(f['rank_slices'][rank]['rows'][1]-f['rank_slices'][rank]['rows'][0] for f in fs),
                actual_binding=b or None,missing=missing,qualified=False))
    # Source operation placement, MTP and all operation coverage need their own
    # literal join; populated-looking stage descriptors cannot bypass it.
    return dict(schema='opentallas.s81.su-stage-coverage.v1',qualified=False,
        physical_stages=81,physical_rank_dies=324,stage_rank_records=records,
        source_SU_node_ids=[n['node'] for n in nodes],
        source_SU_home_assignment_bound=False,MTP_continuation_bound=False,
        he_crom_provider_homes_only=stages['provider_homes'],
        historical_59_programs_are_canonical_coverage=False,
        unbound_stage_rank_records=sum(bool(r['missing']) for r in records),
        unresolved=['literal source SU node to actual instantiated SU/VM home',
                    'all native kernel/operand/ROM/program/core-epoch joins',
                    'MTP continuation programme and actual die instances',
                    'actual boundary activity edges and immutable production duration'])

def require_executable(report):
    if not report.get('qualified'):
        raise ValueError('canonical SU executable coverage incomplete; missing actual homes/programmes/native calendars')
