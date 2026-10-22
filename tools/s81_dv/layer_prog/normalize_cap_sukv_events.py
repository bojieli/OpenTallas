#!/usr/bin/env python3
"""Normalize the shared two-frame CAP/SUKV diagnostic run without replaying RTL.

Raw source logs and image/source identities remain attached. A missing writer,
source RDOUT response, dispatch, completion or future gain consumer remains
explicitly incomplete. This adapter never fabricates a consumer or a lease.
"""
import argparse
from collections import defaultdict, deque
import importlib.util
import sys
import json
from pathlib import Path
import re
import kv_producer_events as E


def normalize(run,source):
    run=Path(run);source=Path(source)
    header=json.loads((run/'identity.json').read_text())
    if header['schema']!=E.SCHEMA or header['run_id']!=E.SHARED_RUN:
        raise ValueError('not the agreed immutable native producer run')
    raw=(run/'run_mut0.log').read_text()
    end=re.search(r'^CAP_SUKV_END cap=(\d+) pair=(\d+) gain=(\d+) bad=(\d+) faults=(\d+) xs=(\d+) capfault=(\d+)$',raw,re.M)
    if not end or tuple(map(int,end.groups()))!=(8,1,1,0,0,0,0) or 'CAP_SUKV_PASS' not in raw:
        raise ValueError('actual eight-value minimum did not report a clean numerical PASS')
    if 'PAIR_MISMATCH' in raw:raise ValueError('actual native pair differed from the source scoreboard')
    tb=source/'tools/s81_dv/tb_cap_sukv.sv'
    if E.sha(tb)!=header['source_sha256'].get('tools/s81_dv/tb_cap_sukv.sv'):
        raise ValueError('actual diagnostic source differs from the run identity')
    result=json.loads((run/'result.json').read_text())
    if result.get('status')!='PASS' or result.get('checks')!={'0':True,'1':True}:
        raise ValueError('shared runner did not pass both actual simulator controls')
    # Check the observed finite end against the pinned source guard. The
    # adapter never creates an end observation from source text alone.
    guard=re.search(r'if\(cyc==(\d+)\)begin\s*\$display\("JSON .*RUN_END',tb.read_text())
    if guard is None:raise ValueError('unrecognized measured replay-end source guard')
    last_edge=int(guard[1]);owner=header['owner'];producer='L2.attn.a_proj'
    capcfg=int((run/'images/capture.hex').read_text().split()[0],16)
    cap_rbase=((capcfg>>29)&0xffff)&0x3fff
    records=[];issues=[];queues=defaultdict(deque);known=defaultdict(int);counter=0
    raw_records=[];legacy_done=[]
    for line in raw.splitlines():
        if line.startswith('JSON '):raw_records.append(json.loads(line[5:]));continue
        m=re.fullmatch(r'EV CAP_WRITE (\d+) (\d+) ([0-9a-fA-F]+)',line)
        if m:
            edge,address=int(m[1]),int(m[2]);row,word=divmod(address,4)
            raw_records.append(dict(record='event',kind='CAP_WRITE',edge=edge,instance='tb_cap_sukv.cap',
                producer=producer,rank=header['source_rank'],source_row=cap_rbase+address,
                scalar_address=address,source_native_row=row,source_word=word,value32=m[3]));continue
        m=re.fullmatch(r'EV GK_DONE (\d+)(?:.*)',line)
        if m:legacy_done.append(dict(record='event',kind='GK_DONE',edge=int(m[1]),
            owner=owner,job=owner+'::GK',command_kind='GK',gain_set=0,
            identity_basis='single source GK command; hardware jid/gain epoch not observed'))
        # New source observations can use JSON directly; no source change is
        # requested merely to match this adapter's labels.
    done_edges={e['edge'] for e in raw_records if e['kind']=='GK_DONE'}
    raw_records.extend(e for e in legacy_done if e['edge'] not in done_edges)
    captures=[e for e in raw_records if e['kind']=='DISPATCH_CAPTURE' and e.get('command_kind')=='GK']
    ends=[e for e in raw_records if e['kind']=='RUN_END']
    if len(ends)!=1 or ends[0]['edge']!=last_edge:
        raise ValueError('actual finite end is absent or differs from the pinned source guard')
    if len(captures)>1:raise ValueError('minimum contains ambiguous multiple actual GK captures')
    gk_job=captures[0]['job'] if captures else owner+'::UNOBSERVED_GK_CAPTURE'
    cap_words=defaultdict(int);cap_masks=defaultdict(int)
    for event in raw_records:
        if event['kind']=='CAP_WRITE':
            row,lane=event['source_native_row'],event['source_word']
            if cap_masks[row]&(1<<lane):raise ValueError('duplicate actual CAP scalar')
            cap_masks[row]|=1<<lane;cap_words[row]|=E.bits(event['value32'],32)<<(32*lane)
    if set(cap_masks)!=set(header['source_native_rows']) or any(m!=15 for m in cap_masks.values()):
        raise ValueError('actual CAP native row ownership differs from selected minimum')
    for event in sorted(raw_records,key=lambda e:e['edge']):
        kind=event['kind'];instance=event.get('instance','');edge=event['edge']
        if kind=='SRAM_COMMIT':
            row=event['row'];m=E.mask4(event['mask']);known[instance,row]|=m
            if '.src.' in instance:
                event.update(producer=producer,producer_kind='native_cap_commit',role='input',
                    intended_consumer_owner=owner,rank=header['source_rank'])
            elif '.dst.' in instance:
                if row in header['target_rows']:
                    event.update(producer=producer,producer_kind='native_carriage_commit',role='input',
                        intended_consumer_owner=owner,rank=header['source_rank'])
                elif 528<=row<=531:
                    event.update(producer='L2.kv_norm.parameter_upload',producer_kind='native_parameter_upload',role='parameter',intended_consumer_owner=owner)
                elif 896<=row<=1023:
                    event.update(producer='L2.kv_norm.gain_upload',producer_kind='native_gain_upload',role='gain',intended_consumer_owner=owner)
                else:raise ValueError('unassigned destination native writer row '+str(row))
            else:raise ValueError('unknown actual native writer instance '+instance)
            records.append(event)
        elif kind=='CARRIAGE_WRITE' and 'word256' in event:
            m=E.bits(event['mask8'],8);word=E.bits(event['word256'],256)
            for lane in range(2):
                sr=event['source_native_row']+lane;dr=event['target_row']+lane
                payload=(word>>(128*lane))&((1<<128)-1)
                if sr not in cap_words or payload!=cap_words[sr] or (m>>(4*lane))&15!=15:
                    raise ValueError('actual carriage pair differs from the actual CAP scalar writers')
                records.append(dict(event,producer=producer,source_native_row=sr,target_row=dr,mask=(m>>(4*lane))&15,
                    word128=f'{payload:032x}',observation_point='destination VP input pin sample'))
        elif kind=='READ_REQUEST' and 'row0' in event:
            if (event['bank0'],event['bank1'])!=(1,1) or event['row0']%2 or event['row1']!=event['row0']+1:
                raise ValueError('this observed pair needs an explicit bank-order mapping')
            pair=[]
            for lane in range(2):
                row=event['row'+str(lane)];read_id=f'{instance}:{counter}:{lane}'
                if '.src.' in instance:read_owner,job=producer,producer+'::RDOUT'
                elif row in header['target_rows']:read_owner,job=owner,owner+'::READBACK_PROBE'
                else:read_owner,job=owner,gk_job
                request=dict(record='event',kind='READ_REQUEST',edge=edge,sram_sample_edge=event['sram_sample_edge'],
                    instance=instance,row=row,read_id=read_id,owner=read_owner,job=job)
                records.append(request);pair.append((read_id,row,known[instance,row]==15))
            counter+=1;queues[instance].append(pair)
        elif kind=='READ_READY' and 'word256' in event:
            if not queues[instance]:raise ValueError('actual extension readback has no native request')
            pair=queues[instance].popleft();word=E.bits(event['word256'],256)
            for lane,(read_id,row,complete) in enumerate(pair):
                if not complete:
                    issues.append(dict(cause='read_has_no_complete_observed_native_writer',instance=instance,row=row,
                        read_id=read_id,edge=edge,raw_word128=f'{(word>>(128*lane))&((1<<128)-1):032x}'))
                    continue
                records.append(dict(record='event',kind='READ_READY',edge=edge,instance=instance,
                    read_id=read_id,row=row,word128=f'{(word>>(128*lane))&((1<<128)-1):032x}'))
        else:records.append(event)
    images={str(p.relative_to(run/'images')):E.sha(p) for p in sorted((run/'images').rglob('*')) if p.is_file()}
    if images!=header.get('runtime_images_sha256'):
        raise ValueError('runtime images differ from the actual simulator identity')
    header.update(raw_log_sha256=E.sha(run/'run_mut0.log'),normalizer_sha256=E.sha(__file__),
        normalization_issues=issues,physical_projection_applied=False,
        runtime_image_sha256=images)
    command_file=run/'images/gk_command.hex'
    if not command_file.is_file():
        raise ValueError('actual compiler-generated GK runtime image is required')
    api_name='tools/s81_dv/layer_prog/kv_bank_contract.py'
    api_path=source/api_name
    api_hash=header.get('reference_source_files_sha256',{}).get(api_name)
    if not api_hash or not api_path.is_file() or E.sha(api_path)!=api_hash:
        raise ValueError('actual compiler API authority is absent or differs from the run readset')
    lower_name='tools/s81_dv/layer_prog/lower_vs.py'
    lower_hash=header.get('reference_source_files_sha256',{}).get(lower_name)
    if not lower_hash or not (source/lower_name).is_file() or E.sha(source/lower_name)!=lower_hash:
        raise ValueError('native command encoder differs from the actual run readset')
    sys.path.insert(0,str(source/'tools/s81_dv'))
    from layer_prog import lower_vs
    if Path(lower_vs.__file__).resolve()!=(source/lower_name).resolve():
        raise ValueError('native command encoder resolved outside the actual run source')
    spec=importlib.util.spec_from_file_location('measured_native_dispatch_api',api_path)
    api=importlib.util.module_from_spec(spec);sys.modules[spec.name]=api;spec.loader.exec_module(api)
    word=int(command_file.read_text().strip(),16)
    if word!=api.dispatch(7,0,0,1024,parameter_base=528,operand_base=896):
        raise ValueError('runtime GK body differs from the existing qualified compiler API')
    header['native_commands']=[dict(command_kind='GK',owner=owner,job=gk_job,word160=f'{word:040x}',
        compiler_api_sha256=E.sha(api_path),runtime_image_sha256=E.sha(command_file),
        native_issue_edge=None,physical_epoch_mapping=None)]
    binary=run/'obj/Vtb_cap_sukv'
    if not binary.is_file() or E.sha(binary)!=header.get('binary_sha256'):
        raise ValueError('actual simulator binary differs from the run identity')
    negative=run/'run_mut1.log'
    header['causal_control']=dict(log_sha256=E.sha(negative),refusal_observed='PAIR_MISMATCH' in negative.read_text()
        and 'CAP_SUKV_FAIL' in negative.read_text()) if negative.exists() else None
    if not header['causal_control'] or not header['causal_control']['refusal_observed']:
        raise ValueError('actual wrong-payload control did not refuse')
    return header,sorted(records,key=lambda e:e['edge'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('preserve prior normalized evidence')
    header,events=normalize(a.run,a.source_root)
    text='\n'.join(json.dumps(e) for e in [header]+events)+'\n'
    a.out.write_text(text)
    print('NORMALIZED',len(events),'actual/source-guarded observations;',len(header['normalization_issues']),'explicit missing writer observations')


if __name__=='__main__':main()
