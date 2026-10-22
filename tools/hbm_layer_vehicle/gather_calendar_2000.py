"""Bind gathers to source-proven producer dates, never to cut fixture images.

The input documents contain source receipts, not tensor values. Missing current
producer or control-route evidence yields a partial manifest with null dates.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from hbm_layer_vehicle.su_indexed_gather_2000 import BANKED_ENGINE,integer,phases,programme_replay


def receipt(spec, root, binding):
    """Load the hashed authority rather than trusting dates copied into a ledger."""
    path=Path(root)/spec['path']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=spec['sha256']:
        raise ValueError('source receipt hash changed: '+str(path))
    record=json.loads(path.read_text())
    if record.get('status')!='PASS':raise ValueError('producer receipt is not PASS: '+str(path))
    if record.get('producer_kind') not in ('native_vm_producer','all_rank_native_arrival','native_vm_allocation','native_control_transport'):
        raise ValueError('fixture, imaged far end or prospective producer is not readiness evidence')
    for field in ('die_sha256','clock_epoch_identity','layer_id'):
        if record.get(field)!=binding[field]:raise ValueError('source receipt has different '+field)
    if not record.get('source_sha256'):raise ValueError('producer source identity absent')
    if record['producer_kind']=='all_rank_native_arrival':
        run=integer(record['aggregation_run'],'actual aggregation run',0,3)
        tp=integer(binding['producer_tp'],'actual source producer TP',96,192)
        if tp not in (96,192) or record.get('producer_tp')!=tp:raise ValueError('actual source producer TP identity required')
        nranks=tp//4
        shards=record.get('source_shards',[])
        if len(shards)!=nranks:raise ValueError('96-word arrival lacks actual source rank shards')
        ranks=set()
        for shard_spec in shards:
            shard=receipt(shard_spec,root,binding)
            rank=integer(shard['rank'],'actual source rank',nranks*run,nranks*(run+1)-1)
            if shard['producer_kind']!='native_vm_producer' or shard.get('producer_tp')!=tp or shard['word_count']!=384//tp:
                raise ValueError('aggregation source must be actual source-owned rank producer')
            if rank in ranks or shard['logical_score_range']!=[384*rank//tp,384*(rank+1)//tp]:
                raise ValueError('duplicated or misassigned actual score shard')
            ranks.add(rank)
            if record['ready_edge']<shard['ready_edge']:
                raise ValueError('arrival precedes native source readiness')
        if record['word_count']!=96:raise ValueError('aggregation native run must contain96 words')
    record['source_receipt']=str(path)+':sha256:'+spec['sha256']
    return record


def build(binding, ledger, requests, receipt_root):
    """Produce the existing compiler binding and F20 replay after all authorities exist.

    Requests provide the actual physical placement of I, four score runs and O.
    Each placement is checked against the corresponding hashed producer/allocation
    receipt. Native dates use the same selected stream-clock epoch throughout.
    """
    missing=[]
    for field in ('die_sha256','source_sha256','clock_epoch_identity','calendar_epoch',
                  'configuration_start','launch_to_calendar_zero','ownership_release_tail',
                  'port_free','parameters','instance','producer_tp','layer_id'):
        if binding.get(field) is None:missing.append('selected gather binding.'+field)
    native=binding.get('bank_calendars') or {}
    for quarter in ('SW','SE','NW','NE'):
        cal=native.get(quarter)
        if not cal:missing.append('native calendar '+quarter+' source profile');continue
        if cal.get('target_id') is None or not cal.get('source_sha256') or not cal.get('instance'):missing.append('native calendar '+quarter+' source identity')
        ages=cal.get('launch_to_bank_owner_edges')
        if not isinstance(ages,list) or len(ages)!=8 or any(age is None for age in ages):
            missing.append('native calendar '+quarter+' actual eight bank owner publication ages')
    if binding.get('status')!='PASS':missing.append('selected gather binding PASS source receipt')
    if len(requests)!=6:raise ValueError('all six route gathers are required')
    for request in requests:
        for key in ('index','run0','run1','run2','run3','output_allocation'):
            name=request['tag']+'::'+key
            if ledger.get(name) is None:missing.append(name+' actual native producer/allocation receipt')
    if ledger.get('control_transport') is None:missing.append('actual native control transport receipt')
    result=dict(schema='opentallas.hbm.gather_calendar.v1',status='PARTIAL',
        qualifies_native_layer=False,qualifies_native_chain=False,
        jobs={r['tag']:dict(start=None,done=None) for r in requests},missing=missing,
        source_binding=deepcopy(binding),
        obligations=['No fixture output, imaged far end, model completion or cut check edge supplies producer readiness.',
                     'Whole token requires actual upstream producers and downstream consumer leases.'])
    if missing:return result
    if binding.get('engine')!=BANKED_ENGINE or binding.get('clock')!='stream':
        raise ValueError('actual selected stream-clock gather engine required')
    if binding.get('control_transport')!='ot_static_program_target' or binding.get('target_id')!=180:
        raise ValueError('released selected F20 gather target 180 required')
    if binding['parameters'].get('SEGMENTED96')!=1 or binding['parameters'].get('NATIVE_BANKED')!=1:
        raise ValueError('actual GSC placement requires selected SEGMENTED96 source')
    control=receipt(ledger['control_transport'],receipt_root,binding)
    if control['producer_kind']!='native_control_transport':raise ValueError('actual control transport authority required')
    for field in ('calendar_epoch','configuration_start','launch_to_calendar_zero','ownership_release_tail','parameters','producer_tp','layer_id','bank_calendars'):
        if control.get(field)!=binding[field]:raise ValueError('control binding differs from hashed source receipt: '+field)
    if control.get('engine_source_sha256')!=binding['source_sha256']:
        raise ValueError('control transport receipt names a different selected engine source')
    profile=phases(binding['parameters']['READ_SAMPLE'],binding['parameters']['WRITE_COMMIT'])
    epoch=integer(binding['calendar_epoch'],'actual calendar epoch',0,2**31-1)
    available=integer(binding['port_free'],'actual bank ownership availability',0,2**31-1)
    if available>epoch:raise ValueError('programme selects native bank ports before their actual owner releases them')
    host_launch=epoch-binding['launch_to_calendar_zero']
    owner_ready=max(host_launch+age for cal in binding['bank_calendars'].values() for age in cal['launch_to_bank_owner_edges'])
    free=max(epoch+2,owner_ready)
    plans=[];jobs={}
    for request in requests:
        tag=request['tag'];d=deepcopy(request['descriptor'])
        producers={key:receipt(ledger[tag+'::'+key],receipt_root,binding)
                   for key in ('index','run0','run1','run2','run3','output_allocation')}
        expected={'index':(d['index_word'],1),'output_allocation':(d['dest_word'],1)}
        if len(d.get('segment_bases',[]))!=4:raise ValueError('actual four GSC native runs required')
        expected.update({f'run{i}':(address,96) for i,address in enumerate(d['segment_bases'])})
        for key,(first,n) in expected.items():
            record=producers[key]
            allowed=('native_vm_allocation',) if key=='output_allocation' else (('native_vm_producer',) if key=='index' else ('all_rank_native_arrival',))
            if key.startswith('run') and record.get('aggregation_run')!=int(key[-1]):raise ValueError('source arrival has wrong logical score run')
            if record['producer_kind'] not in allowed:raise ValueError('incorrect source producer authority '+tag+' '+key)
            integer(first,'actual producer first word',0,(1<<18)-n)
            if (record['first_word'],record['word_count'])!=(first,n):
                raise ValueError('request placement differs from actual source producer '+tag+' '+key)
        ready=max(integer(producers[k]['ready_edge'],'actual native readable edge',0,2**31-1)
                  for k in ('index','run0','run1','run2','run3'))
        output=producers['output_allocation']
        start=max(free,ready+1,integer(output['free_edge'],'output allocation available',0,2**31-1),
                  math.ceil(request['earliest_model_issue']))
        done=start+profile['done']
        for key in ('index','run0','run1','run2','run3'):
            integer(producers[key]['release_edge'],'actual retained producer lifetime',done,2**31-1)
        integer(output['release_edge'],'actual output allocation lifetime',done+2,2**31-1)
        job=dict(index_ready=producers['index']['ready_edge'],
                 score_ready=max(producers[k]['ready_edge'] for k in ('run0','run1','run2','run3')),
                 port_free=start,index_release=producers['index']['release_edge'],
                 score_release=min(producers[k]['release_edge'] for k in ('run0','run1','run2','run3')),
                 output_release=output['release_edge'],descriptor=deepcopy(d),producer_receipts=producers)
        jobs[tag]=job
        plans.append(dict(status='native_gather_emitted',native_gather=dict(tag=tag,descriptor=d,start=start,done=done)))
        free=done+2
    selected=deepcopy(binding);selected['jobs']=jobs
    replay=programme_replay(plans,selected)
    result.update(status='SOURCE_PROGRAMME',jobs=jobs,plans=plans,source_binding=selected,replay=replay,
                  missing=[],calendar_qualified=False,production_enabled=False)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binding',type=Path,required=True)
    p.add_argument('--ledger',type=Path,required=True)
    p.add_argument('--requests',type=Path,required=True)
    p.add_argument('--receipt-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=build(json.loads(a.binding.read_text()),json.loads(a.ledger.read_text()),
                 json.loads(a.requests.read_text()),a.receipt_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],missing=result['missing'])))
if __name__=='__main__':main()
