#!/usr/bin/env python3
"""Build native SUKV programmes from actual source row/clock bindings.

Input readiness is never inherited from model op starts. This builder selects
actual existing operation IDs, derives local command/commit ages from the
qualified source, and schedules only jobs whose real producer-row receipts are
present. Missing CAP/inter-rank receipts remain named work, not zero dates.

The binding names the actual die SHA, selected u_s_3N parameters, source closure,
clock identity, and seqhost native-command epoch. Ledger dates must explicitly be
relative to that command epoch (native row issue zero); raw receiver/absolute
clock edges cannot be substituted. Each owner requires owner::input_rows;
normalizers additionally require owner::parameters and owner::gain_upload_rows.
Each producer record references a hashed JSON receipt containing identical rows,
writes, source kind and clock/command epoch. Rows carry lo/hi, ready_edge,
release_edge, producer, source_receipt and format; optional producer_job names an
already emitted native output dependency. Writes carry the existing lower_kv
native input-write fields. Gain upload records carry an explicit finite
gain_bank_release_edge through the arithmetic consumer's completion. The
builder retains these dates, derives last-read bounds from selected source,
and fails if a lease cannot cover execution. Programme output always remains
unqualified until the emitted jobs run on the selected physical binding.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from dv_layer_compile import Die, ctl_path

DONE=dict(KV=1130,GK=1025,CN=1218,IK=1058,CP=390)
UNIT_RECEIPTS={
    '0576658123f753e2dace8e3549bca06ccd11a6155a9d11ca49c44abcd3eff3aa':0,
    '4d169bcd4bc1edb34574ef4a2cd41c14927eae4bfc865438b3567d1bf9513aee':1,
}
NATIVE_COMMIT_SOURCE={
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv':'d7073948db44727894d838f37b47056749e07890a2ada02ee6fb0f2bd9dc9b15',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v':'6f87b48e0860f3645178d2973638322af7867280a6884809be5e2024b2d91828',
}
TRANSPORT_RECEIPT_SHA='b07a81645924fd52a68d4b25e0ff20594b8bc7d8a8a215fd5b05009821bd4199'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def selected_groups(schedule):
    groups={}
    for op in schedule['ops']:
        name=op['op'].removeprefix('mtp.')
        kind=('CP' if name=='attn.cmp.pool' else
              'CN' if name.startswith('attn.cmp.norm.') or name=='attn.cmp.row_qdq' else
              'IK' if name.startswith('attn.cmp.k_norm.') or name=='attn.cmp.k_rope_qdq' else
              'KV' if name.startswith('attn.kv_norm.') or name=='attn.kv_rope_qdq' else None)
        if kind:groups.setdefault(kind,[]).append(op)
    result=[]
    for kind,ops in groups.items():
        owner=next((o for o in ops if o['op'].endswith('.sumsq')),ops[0])
        result.append(dict(kind=kind,owner=owner['id'],covers=[o['id'] for o in ops],
                           earliest_model_issue=math.ceil(owner['start'])))
    return sorted(result,key=lambda x:(x['earliest_model_issue'],x['kind']))


def derive_profile(die,binding,transport_receipt,unit_receipt):
    if binding['die_v_sha256']!=die.die_sha:
        raise ValueError('native producer binding differs from actual die.v')
    if binding.get('status')!='PASS' or binding.get('instance')!='u_s_3N':
        raise ValueError('actual selected KV slice binding PASS required')
    if sha(transport_receipt)!=TRANSPORT_RECEIPT_SHA or sha(unit_receipt) not in UNIT_RECEIPTS:
        raise ValueError('selected XRT/SUKV timing receipts differ; use a measured source profile')
    hard_rq=UNIT_RECEIPTS[sha(unit_receipt)]
    if binding['parameters'].get('HARD_RQ',0)!=hard_rq:
        raise ValueError('selected HARD_RQ differs from exact measured source profile')
    source=Path(binding['source_root'])
    for name,digest in binding['source_hashes'].items():
        if sha(source/name)!=digest:raise ValueError('bound RTL source changed '+name)
    for name,digest in NATIVE_COMMIT_SOURCE.items():
        if binding['source_hashes'].get(name)!=digest:
            raise ValueError('native VP/SRAM commit source differs '+name)
    unit=json.loads(Path(unit_receipt).read_text())
    if unit.get('status')!='PASS':raise ValueError('qualified SUKV source receipt must pass')
    for name,digest in unit['source_sha256'].items():
        if '/test/' in name or name.startswith('tools/'):continue
        if binding['source_hashes'].get(name)!=digest:
            raise ValueError('SUKV measured source does not match selected component '+name)
    transport=json.loads(Path(transport_receipt).read_text())
    for name,rec in transport['source_pins'].items():
        if binding['source_hashes'].get(name)!=rec['sha256']:
            raise ValueError('XRT transport source does not match selected component '+name)
    if binding['parameters'].get('KV_ENABLE')!=1 or binding['parameters'].get('KV_CNIK')!=1 or binding['parameters'].get('KV_CP')!=1:
        raise ValueError('selected bank must really enable KV/CNIK/CP')
    dl=binding['parameters']['DL']
    if type(dl) is not int or dl<0:raise ValueError('actual downrelay depth required')
    cp=ctl_path(die,'u_s_3N')
    # ctl_path events include RSTOP2. Qualified XRT raw CTL pin->c_v is5;
    # then DL relay, VP pin sample1, SU forward1, KV pin sample1.
    offset=cp['edges']-2+transport['component_edges']['CTL_pin_to_c_v']+dl+3
    return dict(capture_offset=offset,leaf_downrelay=dl,ctl_path=cp,hard_rq=hard_rq,
        source_receipt=str(unit_receipt),source_receipt_sha256=sha(unit_receipt),
        native_commit_source_sha256=NATIVE_COMMIT_SOURCE,
        transport_receipt_sha256=sha(transport_receipt),adapter_done=DONE,
        first_native_write=dict(KV=1030,CN=1030,IK=1030,CP=139),
        last_read_completion_bound=dict(KV=80,CN=80,IK=80,GK=72,CP=378),
        native_write_commit_after_done=1,native_read_ready_after_done=2,
        convention='sampled posedges; finish_edges in SUKV bench counts first capture, so done_age=finish_edges-1',
        derivation=['capture_offset=ctl_path.edges-RSTOP2+XRT5+DL+VP/KV3',
          'norm drain1024: first x_wv after capture+1028, VP captures+1029, SRAM commits+1030',
          'CP64 outputs at period4: first x_wv=done-1-4*63; native commit adds2',
          'last x_wv=done-1; VP captures at done; read-before-write SRAM commits done+1, new read at done+2',
          'last input receipt bounds: reads74/66 or issue-calendar372, plus selected VLAT4 and2 registered edges'])


def build(die,schedule,binding,ledger,transport_receipt,unit_receipt):
    profile=derive_profile(die,binding,transport_receipt,unit_receipt)
    groups=selected_groups(schedule)
    if ledger.get('die_v_sha256')!=die.die_sha or ledger.get('clock_epoch_identity')!=binding['clock_epoch_identity']:
        raise ValueError('producer row dates belong to a different die or clock epoch')
    if ledger.get('edge_convention')!='native_command_epoch_relative_sampled_edges':
        raise ValueError('producer row dates must explicitly use native command epoch relative sampled edges')
    if ledger.get('native_command_epoch_seq_edge')!=binding.get('native_command_epoch_seq_edge') or type(binding.get('native_command_epoch_seq_edge')) is not int:
        raise ValueError('explicit selected seqhost command epoch required; do not cast absolute clock dates')
    jobs=[];missing=[];port_free=0
    for group in groups:
        kind=group['kind'];owner=group['owner']
        # These records come from actual CAP/carriage/parameter producers, not
        # reference tensor outputs or a model reservation. The builder never
        # supplies missing row ready/consumer release dates.
        wanted=[owner+'::input_rows']
        if kind!='CP':wanted+=[owner+'::gain_upload_rows',owner+'::parameters']
        absent=[key for key in wanted if key not in ledger['producers'] or ledger['producers'][key].get('status')!='PASS']
        if absent:
            missing.append(dict(owner=owner,kind=kind,missing_producer_receipts=absent,
                required_native_rows=([[0,511]] if kind=='CP' else [[672,819]]),
                source_requirement='Actual selected die/epoch CAP or native carriage commits, parameter/gain uploads and finite row leases',
                inter_rank_requirement='All four ranks each carry 128 values before a D512 operand is claimed'));continue
        records={key:deepcopy(ledger['producers'][key]) for key in wanted}
        for key,record in records.items():
            if record.get('status')!='PASS' or record.get('producer_kind') in ('fixture_output','prospective_capture_map'):
                raise ValueError('actual source producer receipt required '+key)
            receipt=Path(ledger['receipt_root'])/record['receipt_path']
            if sha(receipt)!=record['receipt_sha256']:raise ValueError('producer receipt changed '+key)
            recorded=json.loads(receipt.read_text())
            for field in ('rows','writes','clock_epoch_identity','producer_kind','status','gain_bank_release_edge','edge_convention','native_command_epoch_seq_edge'):
                if record.get(field)!=recorded.get(field):
                    raise ValueError('producer ledger differs from hashed source receipt '+key+' '+field)
            if record.get('edge_convention')!=ledger['edge_convention'] or record.get('native_command_epoch_seq_edge')!=ledger['native_command_epoch_seq_edge']:
                raise ValueError('source producer rows use a different native command epoch '+key)
            if record.get('clock_epoch_identity')!=binding['clock_epoch_identity']:
                raise ValueError('producer row dates cannot be cast between clock epochs '+key)
        gain_set=3 if kind=='CN' else 0
        capture_offset=profile['capture_offset']
        def append_job(k,rows,covers,earliest,extra):
            nonlocal port_free
            if not rows:raise ValueError('empty actual producer row set '+owner+' '+k)
            ready=max(r['ready_edge'] for r in rows)
            issue=max(earliest,ready+1-capture_offset,port_free-capture_offset,0)
            capture=issue+capture_offset;done=capture+DONE[k]
            lastread=capture+profile['last_read_completion_bound'][k]
            for row in rows:
                if type(row['ready_edge']) is not int or row['ready_edge']>=capture:
                    raise ValueError('actual producer row is not ready '+owner)
                row['last_read_edge']=lastread
                if row['release_edge']<lastread+1:
                    raise ValueError('actual producer lifetime ends before final input read '+owner)
            for write in extra.get('writes',[]):
                if type(write['commit_edge']) is not int or write['commit_edge']>=capture:
                    raise ValueError('actual input write has not committed before capture '+owner)
            job=dict(id=owner+'::'+k,kind=k,covers=covers,owner=owner,issue=issue,
                context=ledger['context'],capture_offset=capture_offset,leaf_downrelay=profile['leaf_downrelay'],
                done_age=DONE[k],release_edge=done+2,source_receipt=str(unit_receipt),
                residency=rows,gain_set=gain_set,jid=ledger['job_ids'][owner],drain_age=1024,**extra)
            if k!='GK':
                job.update(output_ready_edge=done+2,
                    first_output_write_edge=done-251 if k=='CP' else capture+1030)
            port_free=done+1;jobs.append(job);return job
        gain=None
        if kind!='CP':
            # Upload each physical consumer's actual gain payload. KV and IK
            # both use bank0 but have different weights; do not cache by bank#.
            g=records[owner+'::gain_upload_rows']
            gain=append_job('GK',g['rows'],[],max(0,group['earliest_model_issue']-DONE['GK']),
                            dict(parameter_base=528,operand_base=896,writes=g.get('writes',[])))
        rows=records[owner+'::input_rows']['rows']
        if kind!='CP':rows+=records[owner+'::parameters']['rows']
        extra=(dict(slot0_base=0,slot1_base=256,output_base=692) if kind=='CP' else
               dict(parameter_base=672,operand_base=692,
                    gain_residency=dict(gain_set=gain_set,
                       ready_edge=gain['issue']+capture_offset+DONE['GK'],
                       release_edge=records[owner+'::gain_upload_rows']['gain_bank_release_edge'],
                       source_receipt=str(unit_receipt))))
        writes=[]
        for key,rec in records.items():
            if not key.endswith('::gain_upload_rows'):writes+=rec.get('writes',[])
        extra['writes']=writes
        arithmetic=append_job(kind,rows,group['covers'],group['earliest_model_issue'],extra)
        if gain and extra['gain_residency']['release_edge']<arithmetic['issue']+capture_offset+DONE[kind]:
            raise ValueError('actual gain bank lease expires before consumer completion '+owner)
    program=dict(schema='opentallas.s81.kv_program.v1',die_v_sha256=die.die_sha,
        source_binding=binding,source_timing_derivation=profile,jobs=jobs,
        edge_convention=ledger['edge_convention'],native_command_epoch_seq_edge=binding['native_command_epoch_seq_edge'],
        missing=missing,selected_model_operations=groups,
        status='SOURCE_PROGRAMME' if not missing else 'PARTIAL',
        calendar_qualified=False,production_enabled=False,
        next='Bind actual native CAP/carriage row receipts and current source clock/landing dates; run emitted native jobs')
    if jobs:
        from layer_prog.lower_kv import validate
        validate(program,schedule)
    return program


def relative_constraints(schedule,ledger):
    """Keep measured component readiness useful without inventing a die epoch."""
    if ledger.get('schema')!='opentallas.s81.native_producer_ledger.v1' or not ledger.get('source_relative_only'):
        raise ValueError('actual source-relative producer ledger required')
    if ledger.get('edge_convention')!='replay_native_command_epoch_relative_sampled_edges' or ledger.get('physical_projection_applied'):
        raise ValueError('component observations must retain their separate replay edge domain')
    groups=[]
    for group in selected_groups(schedule):
        kind=group['kind'];owner=group['owner']
        required=set(range(512)) if kind=='CP' else set(range(692,820))
        available=[r for r in ledger.get('row_availability',[]) if r.get('intended_consumer_owner')==owner
                   and r['row'] in required and r.get('known_mask')==15 and r.get('ready_edge') is not None]
        rows={r['row'] for r in available};missing=sorted(required-rows)
        gain=ledger.get('producers',{}).get(owner+'::gain_upload_rows') if kind!='CP' else None
        groups.append(dict(group,observed_input_rows=available,missing_input_rows=missing,
            observed_input_values=4*len(rows),missing_input_values=4*len(missing),
            complete_input_ready_edge=max((r['ready_edge'] for r in available),default=None) if not missing else None,
            source_gain_record=gain,arithmetic_dispatch_admitted=False,
            required_next=['Complete actual native operand and parameter commits',
                           'Matched finite row and gain leases for the actual arithmetic consumer',
                           'Explicit selected die clock/route projection into the native issuer epoch']))
    return dict(schema='opentallas.s81.kv_relative_constraints.v1',status='PARTIAL',
        run_id=ledger['run_id'],event_stream_sha256=ledger.get('event_stream_sha256'),
        edge_convention=ledger['edge_convention'],native_clock_domain=ledger['native_clock_domain'],
        physical_epoch_mapping=ledger.get('physical_epoch_mapping'),physical_projection_applied=False,
        native_command_epoch_seq_edge=None,source_sha256=ledger['source_sha256'],
        observed_native_commands=ledger.get('native_commands',[]),groups=groups,
        ranks_observed=ledger.get('ranks_observed',[]),required_ranks_for_D512=[0,1,2,3],
        calendar_qualified=False,production_enabled=False,jobs=[],
        next='Use measured relative source events; keep missing operands, consumer leases and physical clock origin explicit')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree',type=Path)
    p.add_argument('--schedule',type=Path,required=True)
    p.add_argument('--binding',type=Path)
    p.add_argument('--producer-ledger',type=Path,required=True)
    p.add_argument('--transport-receipt',type=Path)
    p.add_argument('--unit-receipt',type=Path)
    p.add_argument('--source-relative-only',action='store_true',help='emit actual partial producer constraints with no physical epoch or native jobs')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('preserve prior programme; choose fresh output')
    if a.source_relative_only:
        result=relative_constraints(json.loads(a.schedule.read_text()),json.loads(a.producer_ledger.read_text()))
        a.out.write_text(json.dumps(result,indent=2)+'\n')
        print('PARTIAL source-relative constraints;',sum(g['observed_input_values'] for g in result['groups']),'observed input values; no physical epoch or full command admission')
        return 2
    if any(x is None for x in (a.tree,a.binding,a.transport_receipt,a.unit_receipt)):
        p.error('full programme emission requires --tree, --binding, --transport-receipt and --unit-receipt')
    result=build(Die(a.tree),json.loads(a.schedule.read_text()),json.loads(a.binding.read_text()),
                 json.loads(a.producer_ledger.read_text()),a.transport_receipt,a.unit_receipt)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],len(result['jobs']),'actual native jobs;',len(result['missing']),'missing producer groups')
    return 0 if not result['missing'] else 2


if __name__=='__main__':sys.exit(main())
