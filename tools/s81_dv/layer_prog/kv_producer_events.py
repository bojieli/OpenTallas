#!/usr/bin/env python3
"""Extract finite relative native row leases from the shared measured replay.

This consumes diagnostic observations, not a new hardware protocol. An actual
SRAM commit makes a word readable on the next sampling edge in the pinned
read-before-write macro. Read values are checked against the version present at
the actual SRAM read-sampling edge. Physical clock/route mapping stays separate.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

SCHEMA='opentallas.s81.native_producer_events.v1'
SHARED_RUN='s81-l2-cap-carriage-sukv-20261021-r1'
MEM='physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v'
MEM_SHA='6f87b48e0860f3645178d2973638322af7867280a6884809be5e2024b2d91828'
KINDS={'CAP_WRITE','CARRIAGE_WRITE','VP_CAPTURE','SRAM_COMMIT','READ_REQUEST','READ_READY',
       'GAIN_LOAD','GK_DONE','GAIN_CONSUME','GAIN_OVERWRITE','DISPATCH_CAPTURE','DONE','RUN_END','FAULT'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integer(value,name,lo=0,hi=2**48-1):
    if type(value) is not int or not lo<=value<=hi:raise ValueError(name+' must be an explicit integer')
    return value


def bits(value,width):
    value=int(value,16) if isinstance(value,str) else value
    return integer(value,'observed bit vector',0,(1<<width)-1)


def mask4(value):
    value=bits(value,128)
    if value<=15:return value
    result=0
    for lane in range(4):
        m=(value>>(32*lane))&0xffffffff
        if m not in (0,0xffffffff):raise ValueError('native mask is not a whole FP32 lane')
        result|=(m!=0)<<lane
    return result


def load(path):
    objects=[]
    for line in Path(path).read_text().splitlines():
        if line.startswith('NATIVE_EVENT '):line=line[len('NATIVE_EVENT '):]
        if not line.strip():continue
        objects.append(json.loads(line))
    if not objects or objects[0].get('record')!='run_identity' or objects[0].get('schema')!=SCHEMA:
        raise ValueError('shared native producer run identity must be the first record')
    return objects[0],objects[1:]


def extract(header,events,source_root):
    if header.get('schema')!=SCHEMA or not header.get('run_id') or not header.get('native_clock_domain'):
        raise ValueError('explicit shared run/source clock identity required')
    integer(header['native_command_epoch_edge'],'native command epoch')
    if header['source_sha256'].get(MEM)!=MEM_SHA:
        raise ValueError('native read-ready derivation requires the actual pinned SRAM source')
    for name,digest in header['source_sha256'].items():
        if sha(Path(source_root)/name)!=digest:raise ValueError('replay source closure changed '+name)
    previous=-1;writes=defaultdict(list);requests={};readbacks=[];dispatch={};done={}
    cap=[];carriage=[];gains=[];faults=[];run_end=None
    for seq,event in enumerate(events):
        if event.get('record')!='event' or event.get('kind') not in KINDS:
            raise ValueError('unsupported native observation record')
        edge=integer(event['edge'],'sampled native edge')
        if edge<previous:raise ValueError('event stream moves backwards in its native clock')
        previous=edge
        if event.get('native_clock_domain',header['native_clock_domain'])!=header['native_clock_domain']:
            raise ValueError('event clock cannot be cast into the replay epoch')
        kind=event['kind'];event=deepcopy(event);event['sequence']=seq
        if kind=='FAULT':faults.append(event);continue
        if kind=='RUN_END':run_end=edge;continue
        if kind=='CAP_WRITE':
            bits(event['value32'],32);cap.append(event);continue
        if kind=='CARRIAGE_WRITE':
            integer(event['target_row'],'carriage target row',0,1023)
            bits(event['word128'],128);mask4(event['mask']);carriage.append(event);continue
        if kind in ('GAIN_LOAD','GK_DONE','GAIN_CONSUME','GAIN_OVERWRITE'):
            integer(event['gain_set'],'gain set',0,3);gains.append(event)
        if kind in ('DISPATCH_CAPTURE','DONE','GK_DONE'):
            key=(event['owner'],event['job'])
            target=dispatch if kind=='DISPATCH_CAPTURE' else done
            if key in target and (kind=='DISPATCH_CAPTURE' or target[key]['edge']!=edge or target[key]['command_kind']!=event['command_kind']):
                raise ValueError('duplicate native dispatch/completion identity')
            target[key]=event
        if kind=='SRAM_COMMIT':
            row=integer(event['row'],'native row',0,1023);m=mask4(event['mask']);word=bits(event['word128'],128)
            if not m:raise ValueError('empty native commit')
            if event.get('producer_kind')=='fixture_output':raise ValueError('fixture output is not an actual producer')
            if not event.get('producer') or not event.get('role'):raise ValueError('native commit lacks writer provenance')
            versions=writes[(event.get('instance',''),row)]
            if versions and versions[-1]['edge']==edge:raise ValueError('two native writers own the same row edge')
            known=versions[-1]['known'] if versions else 0
            combined=versions[-1]['combined'] if versions else 0
            for lane in range(4):
                if m&(1<<lane):
                    combined=(combined&~(0xffffffff<<(32*lane)))|(word&(0xffffffff<<(32*lane)))
            event.update(mask=m,combined=combined,known=known|m)
            versions.append(event)
        elif kind=='READ_REQUEST':
            key=event['read_id']
            if key in requests:raise ValueError('duplicate native read identity')
            sample=integer(event.get('sram_sample_edge',edge),'actual SRAM read sample')
            if sample<edge:raise ValueError('SRAM read cannot precede its request observation')
            event['sram_sample_edge']=sample
            integer(event['row'],'read row',0,1023);requests[key]=event
        elif kind=='READ_READY':readbacks.append(event)
    if faults:raise ValueError('measured native replay reported a source fault')
    if run_end is None:raise ValueError('finite measured RUN_END edge required')
    if run_end<previous:raise ValueError('observation after finite replay end')
    consumed=set();uses=defaultdict(list);observed_reads=[];consumer_versions={}
    for event in readbacks:
        key=event['read_id']
        if key in consumed or key not in requests:raise ValueError('missing or duplicate native read request')
        consumed.add(key);request=requests[key];row=request['row'];sample=request['sram_sample_edge']
        if event['edge']<sample:raise ValueError('native data appears before the SRAM read sample')
        instance=request.get('instance','')
        if event.get('instance','')!=instance:raise ValueError('native read response belongs to another SRAM instance')
        versions=[w for w in writes[(instance,row)] if w['edge']<sample]
        if not versions:raise ValueError('native read has no prior actual writer')
        version=versions[-1]
        if version['known']!=15:raise ValueError('native read includes lanes with no actual producer')
        if bits(event['word128'],128)!=version['combined']:
            raise ValueError('native read differs from read-before-write SRAM version')
        if event.get('row',row)!=row:raise ValueError('read result address differs from request')
        owner=request.get('owner',request.get('consumer'));job=request.get('job')
        if not owner or not job:raise ValueError('native read must name its real consumer owner/job')
        command=dispatch.get((owner,job));completion=done.get((owner,job))
        if command and sample<command['edge']:raise ValueError('native read precedes consumer dispatch')
        if completion and sample>completion['edge']:raise ValueError('native read exceeds consumer completion')
        lease_key=(owner,job,instance,row)
        if lease_key in consumer_versions and consumer_versions[lease_key]!=version['sequence']:
            raise ValueError('native consumer observes two producer versions of one input row')
        consumer_versions[lease_key]=version['sequence']
        uses[(owner,job,instance,row,version['sequence'])].append(sample)
        observed_reads.append(dict(read_id=key,owner=owner,job=job,instance=instance,row=row,sram_sample_edge=sample,
                                   ready_observation_edge=event['edge'],writer_edge=version['edge']))
    pending_reads=sorted(set(requests)-consumed,key=str)
    records=defaultdict(list);pending=[];incomplete_records=set();missing_identity=[]
    for key,completion in done.items():
        command=dispatch.get(key)
        if command and (completion['edge']<command['edge'] or completion['command_kind']!=command['command_kind']):
            raise ValueError('native completion precedes or differs from its actual dispatch')
        if command and 'jid' in command and 'jid' in completion:
            if command['jid']!=completion['jid']:raise ValueError('native completion hardware jid differs from dispatch')
        else:
            missing_identity.append(dict(owner=key[0],job=key[1],cause='hardware_jid_not_observed_at_both_capture_and_completion',
                dispatch_jid=command.get('jid') if command else None,completion_jid=completion.get('jid')))
    for (owner,job,instance,row,version_seq),samples in uses.items():
        version=next(w for w in writes[(instance,row)] if w['sequence']==version_seq)
        command=dispatch.get((owner,job))
        if command is None:
            pending.append(dict(owner=owner,job=job,cause='actual_dispatch_capture_missing'));continue
        leaf_kind=command['command_kind']
        suffix=('gain_upload_rows' if leaf_kind=='GK' else 'parameters' if version['role']=='parameter' else 'input_rows')
        last=max(samples);future=[w['edge'] for w in writes[(instance,row)] if w['edge']>version['edge']]
        if future and min(future)<=last:raise ValueError('actual native writer overwrites a live producer lease')
        complete=(owner,job) in done and not any(requests[k].get('owner',requests[k].get('consumer'))==owner
            and requests[k].get('job')==job for k in pending_reads)
        if not complete:
            incomplete_records.add((owner,suffix))
            pending.append(dict(owner=owner,job=job,cause='consumer_completion_or_read_response_missing'))
        item=dict(lo=row,hi=row,source_instance=instance,ready_edge=version['edge']+1,last_read_edge=last,release_edge=last+1 if complete else None,
                  producer=version['producer'],source_receipt='measured_events.jsonl',
                  format=version.get('format','fp32'),writer_commit_edge=version['edge'],
                  producer_kind=version.get('producer_kind','actual_native_commit'))
        if version.get('producer_job'):item['producer_job']=version['producer_job']
        records[(owner,suffix)].append(item)
    # Raw observations remain available even if the minimum has no full operand
    # or consumer. Such a subset cannot become a complete D512 row manifest.
    clock_identity=header.get('clock_epoch_identity') or hashlib.sha256(json.dumps(
        dict(run_id=header['run_id'],clock=header['native_clock_domain'],source=header['source_sha256']),sort_keys=True).encode()).hexdigest()
    common=dict(clock_epoch_identity=clock_identity,
        edge_convention='replay_native_command_epoch_relative_sampled_edges',
        native_command_epoch_edge=header['native_command_epoch_edge'],native_command_epoch_seq_edge=None)
    producers={}
    for (owner,suffix),rows in records.items():
        record=dict(status='PASS',producer_kind='actual_native_commit',**common,
                    run_id=header['run_id'],event_stream_sha256=header.get('event_stream_sha256'),
                    replay_source_sha256=header['source_sha256'],rows=sorted(rows,key=lambda r:r['lo']),
                    writes=[],scope='MEASURED_SOURCE_RELATIVE_COMPONENT_ONLY')
        if (owner,suffix) in incomplete_records:record['status']='PARTIAL'
        if suffix=='gain_upload_rows':
            loads=[g for g in gains if g['kind']=='GK_DONE' and g.get('owner')==owner]
            uses_gain=[g for g in gains if g['kind']=='GAIN_CONSUME' and g.get('owner')==owner]
            gain_ok=len(loads)==1 and bool(uses_gain)
            if gain_ok:
                load=loads[0];bank=load['gain_set'];loaded=load['edge'];epoch=load.get('gain_epoch')
                upload=dispatch.get((owner,load['job']))
                if epoch is None or upload is None or upload.get('gain_epoch')!=epoch:
                    gain_ok=False
                elif upload.get('gain_set')!=bank or upload['command_kind']!='GK' or upload['edge']>loaded:
                    raise ValueError('GK completion differs from its actual load dispatch')
                actual_loads=[g for g in gains if g['kind']=='GAIN_LOAD' and g.get('owner')==owner
                    and g.get('job')==load['job'] and g.get('gain_epoch')==epoch and g['gain_set']==bank]
                if not actual_loads:gain_ok=False
                if upload and any(not upload['edge']<=g['edge']<=loaded for g in actual_loads):
                    raise ValueError('actual gain load is outside its matching GK dispatch/completion interval')
                ends=[];consumers=set()
                for use in uses_gain:
                    if use.get('gain_epoch')!=epoch or use['gain_set']!=bank:
                        raise ValueError('gain consumer names a different loaded bank/epoch')
                    key=(owner,use['job']);command=dispatch.get(key);completion=done.get(key)
                    if command is None or completion is None:
                        gain_ok=False;continue
                    if command.get('gain_epoch')!=epoch or command.get('gain_set')!=bank:
                        raise ValueError('arithmetic dispatch differs from observed gain epoch')
                    if command['command_kind'] not in ('KV','CN','IK') or command['edge']<=loaded or completion['edge']<command['edge']:
                        raise ValueError('gain consumer capture/completion does not follow GK load')
                    if not command['edge']<=use['edge']<=completion['edge']:
                        raise ValueError('gain consumption is outside the actual consumer interval')
                    ends.append(completion['edge']);consumers.add(key)
                expected={key for key,c in dispatch.items() if key[0]==owner and c['command_kind'] in ('KV','CN','IK')}
                gain_ok=gain_ok and bool(ends) and consumers==expected
                if gain_ok:
                    end=max(ends)
                    if any(g['gain_set']==bank and loaded<g['edge']<=end and
                           g['kind'] in ('GAIN_LOAD','GAIN_OVERWRITE','GK_DONE') for g in gains):
                        raise ValueError('gain bank overwritten before consumer completion')
                    record.update(gain_bank_release_edge=end+1,gain_bank_loaded_edge=loaded,gain_set=bank,gain_epoch=epoch)
            if not gain_ok:
                record['status']='PARTIAL'
                pending.append(dict(owner=owner,cause='matched_finite_gain_consumer_bank_epoch_missing'))
        producers[owner+'::'+suffix]=record
    return dict(schema='opentallas.s81.native_producer_ledger.v1',run_id=header['run_id'],**common,
        die_v_sha256=header.get('die_v_sha256'),physical_epoch_mapping=header.get('physical_epoch_mapping'),
        context=header.get('context'),job_ids={owner:event['jid'] for (owner,job),event in dispatch.items()
            if event.get('command_kind')!='GK' and 'jid' in event},
        native_clock_domain=header['native_clock_domain'],source_sha256=header['source_sha256'],
        native_commands=header.get('native_commands',[]),
        evidence_identity={k:header.get(k) for k in ('raw_log_sha256','binary_sha256','runtime_image_sha256','normalization_issues','causal_control')},
        status='MEASURED_RELATIVE_COMPONENT',source_relative_only=True,physical_projection_applied=False,
        calendar_qualified=False,production_enabled=False,
        ranks_observed=sorted({e['rank'] for e in cap+carriage if 'rank' in e}),
        required_ranks_for_D512=[0,1,2,3],
        producers=producers,pending=pending,pending_reads=pending_reads,missing_identity=missing_identity,
        row_availability=[dict(instance=instance,row=row,known_mask=versions[-1]['known'],
            last_commit_edge=versions[-1]['edge'],
            ready_edge=versions[-1]['edge']+1 if versions[-1]['known']==15 else None,
            word128=f"{versions[-1]['combined']:032x}",
            future_consumer_release_edge=None,producer=versions[-1]['producer'],
            intended_consumer_owner=versions[-1].get('intended_consumer_owner'))
            for (instance,row),versions in writes.items() if versions],
        observed=dict(cap_writes=cap,carriage_writes=carriage,reads=observed_reads,
                      native_commits=[w for versions in writes.values() for w in versions],dispatch=list(dispatch.values()),done=list(done.values())),
        completeness='One minimum subset never implies four ranks or a full D512 input. Missing native rows remain missing.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--events',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('preserve prior extraction; choose a fresh output')
    header,events=load(a.events);header['event_stream_sha256']=sha(a.events)
    ledger=extract(header,events,a.source_root)
    a.out.mkdir(parents=True);copied=a.out/'measured_events.jsonl';copied.write_bytes(a.events.read_bytes())
    ledger.update(receipt_root=str(a.out.resolve()),event_stream_sha256=sha(copied),extractor_sha256=sha(__file__))
    for key,record in ledger['producers'].items():
        path=a.out/(key.replace(':','_')+'.json');path.write_text(json.dumps(record,indent=2)+'\n')
        record.update(receipt_path=path.name,receipt_sha256=sha(path))
    (a.out/'producer_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
    print('EXTRACTED',len(ledger['producers']),'relative producer records;',len(ledger['pending']),'pending authorities; production unbound')


if __name__=='__main__':main()
