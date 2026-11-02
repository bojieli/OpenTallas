#!/usr/bin/env python3
"""Compile a relocatable native HEAD CALR event from the actual selected image.

Emits real machine commands and exact replacement sites. Unresolved executable
issue-time relocations prevent mask emission; no dates are guessed or activated.
"""
import argparse,hashlib,json
from pathlib import Path
import dv_lower as D
import residual2_calendar_candidate as R


def build(calendar):
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
    retired={e['index']for e in cfg}
    return dict(schema='opentallas.qwen.native-head-calr-object.v1',status='RELOCATABLE_NOT_EXECUTABLE',
      source_calendar_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in calendar.iterdir()if p.name in ('dw.hex','calendar_m0.viamap.hex','calendar_m1.viamap.hex')},
      root_patches=patches,retired_head_cfg=[dict(index=e['index'],edge=e['edge'],cmd=f"{e['cmd']:029x}")for e in cfg],
      native_apply_commands=[dict(slice=s,cmd=f'{D.cmd_su(16,s):029x}',pidx=16,user_relocation='actual CALR +128*user',issue_symbol=f'HEAD_APPLY_S{s}_ISSUE')for s in range(12)],
      retained_head_commands=[dict(old_index=e['index'],old_edge=e['edge'],cmd=f"{e['cmd']:029x}")for e in head if e['index']not in retired],
      local37_range=dict(first=1012,count=1,entry=f'{((8<<116)|local37):032x}',stage=37,users='same range invoked peruser by existing OPSEG',start_symbol='HEAD_TABLE_INSTALL_START'),
      layout=dict(old_nent=nent,new_nent=1013,head_first=476,old_head_entries=320,retained_head_entries=308,new_apply_entries=12,new_head_entries=320,remaining_count_capacity=10),
      unresolved_relocations=['HEAD_APPLY_S0..S11_ISSUE from measured native H stream profile and peruser SU lease',
        'HEAD_TABLE_INSTALL_START and exclusive loader/stream window',
        'final residual RSTD publication through last H operand read, including actual native front/transport latency',
        'actual native headtap/Xfill readiness and repriced retained HEAD consumer dates'],
      required_component_receipts=['native ROOT amnb6 noninterference+sixcandidate AMAX+lease controls',
        'native H48case FP32/BF16 output timing+gain/user/rawX controls','actual CTLM37 LOCAL4 defaultoff/on range/user controls'],
      executable=False,mask_emission='REFUSED_UNTIL_ALL_EXECUTION_RELOCATIONS_ARE_LINKED',physical_adoption=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--calendar',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=build(a.calendar);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['layout']))
