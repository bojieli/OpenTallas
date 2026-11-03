#!/usr/bin/env python3
"""Relocate actual HEAD STN/AMAX command fields to the native S8 owner map.

Reads only the selected small CALR image and encoded source/metadata. No tensors,
execution dates or active image are emitted. Existing slice2 commands are controls.
"""
import argparse,hashlib,json
from pathlib import Path
import dv_lower as D
import dv_lower_mat as M
import residual2_calendar_candidate as R
import hdc_isa as ISA

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def build(calendar,plan,gme):
    words,dw=R.decode_image(calendar);head=R.entries(words,dw[3]);old=D.ownership(plan,'slice2')['lm_head'];newown=D.ownership(plan,'s8');new=newown['lm_head']
    ob={b['block']:b for b in old['blocks']};nb={b['block']:b for b in new['blocks']}
    receivers=sorted({b['slice']for b in nb.values()})
    if receivers!=[1,3,5,6,8,10] or len(ob)!=149 or len(nb)!=149:raise ValueError('actual TP8/G3072 HEAD owner geometry required')
    remap={s:s^1 if s<6 else s for s in range(12)};sts=[e for e in head if e['decoded']['kind']==2]
    if len(sts)!=298:raise ValueError('actual selected298 HEAD STNs required')
    layout=M.btab_layout(newown)['lm_head'];btab={e['block']:(s,e)for s,l in layout.items()for e in l}
    fin=[]
    for e in sts:
        d=e['decoded']
        if d['amax']:
            block=d['dbase']//128
            if d['dbase']%128 or d['dst']!=ob[block]['slice'] or d['mode']!=2:raise ValueError('selected legacy receiver/source row mismatch')
            ns,be=btab[block]
            if ns!=remap[d['dst']] or d['sbase']!=be['sbase'] or d['nwords']!=be['words']:raise ValueError('actual S8 BTAB range join mismatch')
            fin.append(block)
        elif d['mode']!=3:raise ValueError('actual L9 sender mode required')
    if sorted(fin)!=list(range(149)):raise ValueError('HEAD row blocks must cover exactly once')
    clear=[e for e in head if e['cmd']==D.cmd_amax(15,clear=1)]
    emits=[e for e in head if e['decoded']['kind']==6 and (e['cmd']>>5)&1]
    if len(clear)!=1 or sorted(e['decoded']['dst']for e in emits)!=[0,2,4,6,8,10]:raise ValueError('actual legacy HEAD AMAX controls differ')
    ranks=[];g=json.loads(gme.read_text())
    for r in g['ranks']:
        row0=r['global_vocabulary_row0'];patch=[]
        if M.STN_KC['lm_head']!=8 or any(ISA.decode(int(q['word_hex'],16))['me_k']!=8 for q in r['programme_words'][:4]):raise ValueError('native STN KC must match all genuine HEAD k8 descriptors')
        for e in sts:
            d=e['decoded'];s=remap[d['dst']];cmd=(e['cmd']&~(15<<112))|(s<<112)
            cmd=(cmd&~(255<<59))|((M.STN_KC['lm_head']-1)<<59)
            if d['amax']:
                row=row0+d['dbase'];cmd=(cmd&~(((1<<24)-1)<<26))|(row<<26)
                if row+16*d['nwords']>row0+18992:raise ValueError('global vocabulary row overflow')
            patch.append(dict(old_index=e['index'],old_cmd=f'{e["cmd"]:029x}',new_cmd=f'{cmd:029x}',new_dst=s,role='receiver' if d['amax']else 'sender',old_kc=d['kc'],native_kc=M.STN_KC['lm_head'],old_date_context=e['edge'],issue_symbol=f'HEAD_STN_I{e["index"]}_ISSUE'))
        ep=[dict(old_index=e['index'],old_cmd=f'{e["cmd"]:029x}',new_cmd=f'{D.cmd_amax(remap[e["decoded"]["dst"]],emit=1):029x}',receiver=remap[e['decoded']['dst']],issue_symbol=f'HEAD_AMAX_EMIT_S{remap[e["decoded"]["dst"]]}')for e in emits]
        ranks.append(dict(rank=r['rank'],global_vocabulary_row0=row0,STN=patch,AMAX_emits=ep,source_weight_metadata_sha256=r['weight_metadata_sha256']))
    return dict(schema='opentallas.qwen.native-head-s8-station-event.v1',status='RELOCATABLE_SOURCE_NOT_EXECUTABLE',default_enabled=False,source_calendar={p.name:sha(p)for p in calendar.iterdir()if p.name in ('dw.hex','calendar_m0.viamap.hex','calendar_m1.viamap.hex')},source_plan_sha256=sha(D.ROOT/plan),source_GME_sha256=sha(gme),old_receivers=[0,2,4,6,8,10],new_receivers=receivers,native_KC=M.STN_KC['lm_head'],KC_contract='native station cfg_kcm1 keeps k=kc-1 block; all genuine HEAD instructions have k8',STN_count=298,AMAX_emits_count=6,source_blocks=149,rows_per_rank=18992,finishing_words_by_slice={s:sum(e['words']for e in es)for s,es in layout.items()},retire_clear_index=clear[0]['index'],new_clears=[dict(dst=s,cmd=f'{D.cmd_amax(s,clear=1):029x}',issue_symbol=f'HEAD_AMAX_CLEAR_S{s}')for s in receivers],added_commands=5,ranks=ranks,remaining=['all native issue/transport/receiver lease dates','current82190/f79 boundary and complete programme qualification','actual eight-rank collective/gather source join'],cycles='unresolved executable dates; no runtime latency adopted',physical_adoption=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('calendar','plan','gme','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();r=build(a.calendar,a.plan,a.gme);a.out.write_text(json.dumps(r,indent=2)+'\n');print('HEAD_S8_STN_SOURCE',r['STN_count'],r['new_receivers'],'extra commands',r['added_commands'])
