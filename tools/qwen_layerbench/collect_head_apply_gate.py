#!/usr/bin/env python3
"""Collect a completed current-source HEAD arithmetic/profile component run.

Command dates begin at the projection's actual cmd_i sampling edge. This does
not assert an upstream CALR/FDN/RP/CTL date, or install the HEAD programme.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path


def collect(packet, output, previous=None):
    prep=json.loads((packet/'preparation.json').read_text())
    run=packet/'baseline';log=(run/'base.log').read_text();status=(run/'status').read_text()
    if 'PASS_NATIVE_HEAD_APPLY_COMPONENT' not in status or 'NATIVE_HEAD_APPLY_PASS cases48 words16384' not in log:
        raise ValueError('completed 48-case native HEAD pass with controls required')
    dates=[]
    for line in log.splitlines():
        if line.startswith('HEAD_NATIVE_DATES '):
            d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
            if not 0<=d['slice']<12 or not 0<=d['user']<4:raise ValueError('invalid source ownership')
            dates.append(d)
    if len(dates)!=48 or {(x['slice'],x['user']) for x in dates}!={(s,u) for s in range(12) for u in range(4)}:
        raise ValueError('complete distinct per-case command/operand/write/stream dates required')
    controls={}
    for name in ('MUT_GAIN','MUT_RAW_X','MUT_USER'):
        text=(run/(name+'.log')).read_text()
        witness=next((line for line in text.splitlines() if re.search('HEAD_NATIVE_VALUE|HEAD_WRONG_OUTPUT_ADDR|HEAD_BF16_VALUE',line)),None)
        rc=re.search(r'^'+name+r'=([0-9]+)$',status,re.M)
        if not witness or not rc or int(rc[1])==0:raise ValueError(name+' not caught')
        controls[name]=dict(result='CAUGHT',exit=int(rc[1]),witness=witness)
    old=json.loads(previous.read_text()) if previous else None
    per=[]
    for s in range(12):
        group=[d for d in dates if d['slice']==s]
        ages=[{k:d[k] for k in ('read_age','operand_age','write_age','stream_age')} for d in group]
        if any(x!=ages[0] for x in ages[1:]):raise ValueError('profile depends on user')
        profiles=[]
        for u in range(4):
            rows=[]
            for line in log.splitlines():
                if line.startswith(f'NATIVE_HEAD_BEAT slice{s} user{u} '):
                    m=re.search(r'eaddr(\d+) offset(\d+)',line)
                    if not m:raise ValueError('bad BF16 event')
                    rows.append(dict(eaddr=int(m[1]),offset=int(m[2])))
            profiles.append(rows)
        if not profiles[0] or any(x!=profiles[0] for x in profiles[1:]):raise ValueError('non-static BF16 profile')
        n=384 if s<8 else 256
        if len(profiles[0])!=n//64:raise ValueError('BF16 coverage')
        last_write=[x['last_write']-x['calr_sample'] for x in group]
        last_stream=[x['last_bf16']-x['calr_sample'] for x in group]
        if len(set(last_write))!=1 or len(set(last_stream))!=1:raise ValueError('last receiver age depends on user')
        receiver_beats=[dict(eaddr=x['eaddr'],offset=ages[0]['stream_age']+x['offset']-profiles[0][0]['offset']) for x in profiles[0]]
        if receiver_beats[-1]['offset']!=last_stream[0]:raise ValueError('receiver stream dates disagree')
        entry=dict(slice=s,users=[0,1,2,3],FP32_words=n,command_input_ages=dict(ages[0],last_write_age=last_write[0],last_stream_age=last_stream[0]),BF16_receiver_beats=receiver_beats,BF16_stream_beats=profiles[0])
        if old:
            before=next(x for x in old['slices'] if x['slice']==s)['BF16_stream_beats']
            if [x['eaddr'] for x in before]!=[x['eaddr'] for x in profiles[0]]:raise ValueError('previous source address order differs')
            entry['prior_source_stream_offset_deltas']=[b['offset']-a['offset'] for a,b in zip(before,profiles[0])]
        per.append(entry)
    result=dict(schema='opentallas.qwen.native-head-emission-profile.v2',status='PASS_COMPONENT',
        memory_profile=prep['memory_profile'],source_projection_metadata=prep['source_projection_metadata'],
        stage_sha256=prep['stage_sha256'],stream_source_sha256=prep['stream_source_sha256'],
        source_allocation=dict(gain_base=1088,apply_pidx=16,x_base=0,rstd_addr=400,VM_user_stride=4096,CROM_user_stride=2048,PROG_user_stride=128,authority='exact fixed allocation validated by prepare_head_apply_gate against actual committed stage payload'),
        source_packet_sha256=hashlib.sha256((packet/'packet.sha256').read_bytes()).hexdigest(),
        clock=dict(period_ps=833,testbench_timescale='1ns/1fs'),cases=48,FP32_words=16384,
        checkpoint_gain_elements=4096,BF16_beats=256,controls=controls,slices=per,actual_case_sampling_edges=dates,
        origin='Direct native SU component cmd_i input sampling edge; global CALR, FDN/RP/CTL and final-bound transport excluded',
        operand_event='posedge receiver consumption of qfd_dv_safe1_lane.s1_v marking native S2 operand capture',
        prior_profile=dict(path=str(previous),sha256=hashlib.sha256(previous.read_bytes()).hexdigest(),comparison_only_no_qualification_transfer=True) if previous else None,
        template_guard='head_native_contract.py selected825 profile3/0 unchanged; new3/1 requires separate measured programme date join',
        qualification_scope='actual current SUVM/eight heads/production BF16 stream and genuine released-checkpoint gains; no ROOT/global lease/calendar/pair/token adoption',
        canonical_activation=False)
    output.write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--packet',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--previous-profile',type=Path)
    a=ap.parse_args();r=collect(a.packet,a.out,a.previous_profile)
    print(json.dumps(dict(status=r['status'],profile=r['memory_profile'],slices=len(r['slices']),first=r['slices'][0],controls={k:v['result'] for k,v in r['controls'].items()})))

if __name__=='__main__':main()
