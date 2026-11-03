#!/usr/bin/env python3
"""Compile a relocatable native HEAD CALR event from the actual selected image.

Emits real machine commands and exact replacement sites. Unresolved executable
issue-time relocations prevent mask emission; no dates are guessed or activated.
"""
import argparse,hashlib,json
from pathlib import Path
import dv_lower as D
import residual2_calendar_candidate as R


def build(calendar, monitor_slice=None, s8_event=None, rank=0, front_event=None):
    if monitor_slice is not None and monitor_slice not in range(12):raise ValueError("monitor slice must be native0..11")
    words,dw=R.decode_image(calendar);base=R.entries(words,dw[2]);head=R.entries(words,dw[3])
    cfg=[e for e in head if e['decoded']['kind']==3]
    if len(head)!=320 or len(cfg)!=12 or sorted(e['decoded']['dst']for e in cfg)!=list(range(12)):
        raise ValueError('actual selected320-entry/12CFG HEAD required')
    earlier=[e for e in base if e['decoded']['kind']==3][-12:]
    if len(earlier)!=12:raise ValueError('actual final residual CFG cohort required')
    bydst={e['decoded']['dst']:e for e in earlier};patches=[]
    for e in cfg:
        p=bydst[e['decoded']['dst']];a=dict(p['decoded']);b=dict(e['decoded'])
        if a.pop('amnb')!=0 or b.pop('amnb')!=(6 if a['root']else 0) or a!=b:
            raise ValueError('HEAD config differs beyond the exact rootAMNB6 prearm')
        if a['root']:
            c=p['cmd']|(6<<97)
            patches.append(dict(index=p['index'],old_cmd=f"{p['cmd']:029x}",new_cmd=f'{c:029x}',edge=p['edge'],changed_field='amnb0->6'))
    if len(patches)!=1 or any(e['decoded']['kind']==6 or e['decoded'].get('amax')for e in base):
        raise ValueError('BASE AMAX traffic or ROOT ownership differs')
    streams=[e for e in base if e['decoded']['kind']==5][-12:]
    if len(streams)!=12 or any(e['cmd']!=D.cmd_stream(s,1 if s==0 else 3,1)for s,e in enumerate(streams)) or any(e['decoded']['kind']==5 for e in head):
        raise ValueError('actual retained residual2 STREAM setup differs')
    nent=dw[0]&1023
    if nent!=1009:raise ValueError('selected1009-entry layout required')
    for s in range(1,37):
        i=868+4*(s-1);e=(words[i//4]>>(128*(i%4)))&((1<<128)-1)
        if (e>>116)!=8 or (e&((1<<116)-1))!=((14<<112)|(s<<4)|9):
            raise ValueError('actual shared LOCAL4 source range differs')
    for i in (474,475):
        if ((words[i//4]>>(128*(i%4)))&((1<<128)-1))!=(1<<116):
            raise ValueError('HEAD alignment padding differs')
    local37=(14<<112)|(37<<4)|9
    seg28=(14<<112)|(28<<4)|5
    retired={e['index']for e in cfg}
    front=None
    if front_event is not None:
        front=json.loads(front_event.read_text())
        if front['status']!='SOURCE_TRANSPORT_EQUATIONS_NOT_EXECUTABLE_DATES' or [e['slice']for e in front['rows']]!=list(range(12)):raise ValueError('actual full native command front source required')
    station=None;overrides={};extra_clears=[]
    if s8_event is not None:
        station=json.loads(s8_event.read_text());rr=station['ranks'][rank]
        if rr['rank']!=rank or station['new_receivers']!=[1,3,5,6,8,10] or station['native_KC']!=8:raise ValueError('complete native S8 station source event required')
        for e in rr['STN']+rr['AMAX_emits']:
            old=next(x for x in head if x['index']==e['old_index'])
            if e['old_cmd']!=f"{old['cmd']:029x}":raise ValueError('station event mismatches selected source calendar')
            overrides[e['old_index']]=e
        retired.add(station['retire_clear_index']);extra_clears=station['new_clears']
    new_head=len(head)-len(cfg)-(1 if station else 0)+12+1+len(extra_clears)
    later_delta=((476+new_head+3)//4)*4-796
    local_first=((nent+later_delta+3)//4)*4
    new_nent=local_first+1
    if new_nent>1023:raise ValueError('native HEAD source exceeds actual10bit CALR count')
    return dict(schema='opentallas.qwen.native-head-calr-object.v1',status='RELOCATABLE_NOT_EXECUTABLE',
      source_calendar_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in calendar.iterdir()if p.name in ('dw.hex','calendar_m0.viamap.hex','calendar_m1.viamap.hex')},
      root_patches=patches,retired_head_cfg=[dict(index=e['index'],edge=e['edge'],cmd=f"{e['cmd']:029x}")for e in cfg],
      retained_stream_setup=dict(extra_commands=0,tag=1,source_calls=[dict(index=e['index'],slice=i,edge=e['edge'],dirs=1 if i==0 else 3,cmd=f"{e['cmd']:029x}")for i,e in enumerate(streams)],lifetime='retained through HEAD; LOCAL4 tables do not rewrite cfg',headtap='actual s6 tap exposes X valid/address/data, no tag'),
      native_apply_commands=[dict(slice=s,cmd=f'{D.cmd_su(17 if s==monitor_slice else 16,s):029x}',pidx=17 if s==monitor_slice else 16,native_SU_input_age=front['rows'][s]['TT_to_native_SU_command']if front else None,native_SU_input_symbol=f'HEAD_NATIVE_SU_S{s}_CMD',user_relocation='actual CALR +128*user',issue_symbol=f'HEAD_APPLY_S{s}_ISSUE')for s in range(12)],
      retained_head_commands=[dict(old_index=e['index'],old_edge_context=e['edge'],cmd=overrides[e['index']]['new_cmd']if e['index']in overrides else f"{e['cmd']:029x}",issue_symbol=overrides[e['index']]['issue_symbol']if e['index']in overrides else f"HEAD_RETAINED_I{e['index']}_ISSUE")for e in head if e['index']not in retired],
      native_front_join=dict(event_sha256=hashlib.sha256(front_event.read_bytes()).hexdigest(),status='SOURCE_EQUATIONS_ONLY')if front else dict(status='REQUIRED_UNRESOLVED'),
      native_s8_station_join=dict(rank=rank,event_sha256=hashlib.sha256(s8_event.read_bytes()).hexdigest(),status='SOURCE_ONLY')if station else dict(status='REQUIRED_UNRESOLVED'),
      native_AMAX_clears=extra_clears,
      native_monitor=dict(slice=monitor_slice,pidx=17,other_pidx=16,source_observer='primary user only',status='UNRESOLVED_EARLIEST_SLICE' if monitor_slice is None else 'SOURCE_CANDIDATE_ONLY'),
      witness_profile=dict(module='qfd_dv_typed_witness_control_head37',HEAD_STAGE37=1,records=15,groups=[dict(pidx=17,slices='earliest singleton'),dict(pidx=16,slices='other eleven')],production_digest='must be recomputed after resolved source issue dates; test digest is not production authority'),
      native_GME_start=dict(cmd=f'{seg28:029x}',base=28,issue_symbol='HEAD_GME_SEGMENT_START',extra_commands=1),
      later_range_relocation=dict(old_first_min=796,entry_index_delta=later_delta,includes=['BOOT','OPSEG stage0 init','all36 existing LOCAL4 preloads'],reason=f'HEAD320→{new_head} requires next four-entry alignment'),
      local37_range=dict(first=local_first,count=1,entry=f'{((8<<116)|local37):032x}',stage=37,users='same range invoked peruser by existing OPSEG',start_symbol='HEAD_TABLE_INSTALL_START'),
      layout=dict(old_nent=nent,new_nent=new_nent,head_first=476,old_head_entries=320,retained_head_entries=len(head)-len(retired),new_apply_entries=12,new_GME_start_entries=1,new_head_entries=new_head,remaining_count_capacity=1023-new_nent),
      unresolved_relocations=['HEAD_APPLY_S0..S11_ISSUE from measured native H stream profile and peruser SU lease',
        'HEAD_TABLE_INSTALL_START and exclusive loader/stream window; explicit LOCAL_SEG28 starts GME/XPF beforeH',
        'final residual RSTD publication through last H operand read, including actual native front/transport latency',
        'actual native headtap/Xfill readiness and repriced retained HEAD consumer dates'],
      required_component_receipts=['native ROOT amnb6 noninterference+sixcandidate AMAX+lease controls',
        'native H48case FP32/BF16 output timing+gain/user/rawX controls','actual CTLM37 LOCAL4 defaultoff/on range/user controls'],
      executable=False,mask_emission='REFUSED_UNTIL_ALL_EXECUTION_RELOCATIONS_ARE_LINKED',physical_adoption=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--calendar',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--monitor-slice',type=int,choices=range(12));p.add_argument('--s8-event',type=Path);p.add_argument('--rank',type=int,choices=range(8),default=0);p.add_argument('--front-event',type=Path);a=p.parse_args();r=build(a.calendar,a.monitor_slice,a.s8_event,a.rank,a.front_event);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['layout']))
