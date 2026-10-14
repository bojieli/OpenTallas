#!/usr/bin/env python3
"""Check every native token stage against actual functional provider capacities."""
import argparse, hashlib, json
from pathlib import Path
import hdc_isa as I
import hdc_qwen_fullshape_isa_w12 as ISA

def check(directory, *, sw=64, lv=6, groups=3072, provider_nw=16, token_nw=18, aw=24, paw=12):
    plan=json.loads((directory/'token_source_plan.json').read_text())
    if plan['groups']!=groups or groups!=3072 or sw!=64:
        raise ValueError('native placement/SU width must match actual provider')
    if token_nw<18 or provider_nw<16 or aw<24 or paw<12:
        raise ValueError('actual token/address/program widths insufficient')
    stages=[(0,'embedding_program.hex','embedding')]+[(n+1,'layer_candidate_program.hex','layer') for n in range(36)]+[(37,'head_program_rank0.hex','head')]
    results=[]
    for stage,name,kind in stages:
        names=[f'head_program_rank{rank}.hex' for rank in range(8)] if kind=='head' else [name]
        operations=[]
        for name in names:
            path=directory/name
            if hashlib.sha256(path.read_bytes()).hexdigest()!=plan['files_sha256'][name]:
                raise ValueError('program pin changed: '+name)
            words=path.read_text().split()
            if len(words)>1<<paw:raise ValueError('programROM capacity')
            for pc,word in enumerate(words):
                f=ISA.decode_instruction(int(word,16))
                if f['unit']==I.UNIT_SU:
                    nout,nin=f['su_nout'],f['su_nin']
                    if f['su_d_nin']:raise ValueError('unvalidated dynamic SU length')
                    if max(nout,nin)>=1<<provider_nw:raise ValueError('SU count width')
                    if f['red'] and nin>sw*(1<<lv):
                        raise ValueError(f'stage{stage} PC{pc} reduction{nin} exceeds SW{sw}*2^LV{lv}')
                    for role in ('a','b','c','d'):
                        base=f[role+'_base']
                        last=base+max(0,nout-1)*f[role+'_so']+max(0,nin-1)*f[role+'_si']
                        if last>=1<<aw:raise ValueError('static operand address width')
                    used=['a']
                    if f['ma']==I.MA_AB or f['md']==I.MD_B or f['ad']==I.AD_NEGB:used.append('b')
                    if f['mb']!=I.MB_OFF or f['ad']==I.AD_C or f['mc']==I.MC_C:used.append('c')
                    if f['dst']==I.DST_VM:used.append('d')
                    for role in used:
                        if f[role+'_d']:continue # source-bound DYN embedding/current-KV handled by owning provider
                        last=f[role+'_base']+max(0,nout-1)*f[role+'_so']+max(0,nin-1)*f[role+'_si']
                        alt=f.get(role+'_src',0)
                        if not alt and last>=plan['required_core']['VM_elements']:raise ValueError('actual VM/scratch region capacity')
                        if alt and role in ('b','c'):
                            capacity=4096 if kind=='head' else plan['layer_crom_words']
                            if last>=capacity:raise ValueError('actual constant bank capacity')
                    if f['red'] and f['r_base']+max(0,nout-1)*f['r_so']>=plan['required_core']['VM_elements']:
                        raise ValueError('actual reducer destination capacity')
                    if kind!='embedding' and f['a_d']==I.DYN_EMBED:
                        raise ValueError('NW16 local provider consumes token-dependent embedding address')
                    if kind=='embedding' and f['a_d']==I.DYN_EMBED:
                        if sw!=64 or 151936*64>1<<aw:raise ValueError('actual reconstructed embedding code-bank address capacity')
                    operations.append({'program':name,'pc':pc,'unit':'SU','nout':nout,'nin':nin,
                                       'reduction_elements':nin if f['red'] else 0,'max_reduce_elements':sw*(1<<lv)})
                elif f['unit']==I.UNIT_ME:
                    split=1<<f['me_split']
                    if f['me_wsrc']:
                        if f['me_nout']!=512 or f['me_k']!=128:raise ValueError('actual fused service shape mismatch')
                    else:
                        if groups%split:raise ValueError('ME split not divisor of actual group count')
                        capacity=(groups//split)*16*8*f['me_tiles']
                        if f['me_nout']>capacity:raise ValueError('ME tile/output capacity')
                        if f['me_row0']+f['me_nout']>1<<provider_nw:raise ValueError('local ME row count/index width')
                        code_capacity=1600 if kind=='head' else 512
                        scale_capacity=1200 if kind=='head' else 816
                        if f['me_wbase']+f['me_tiles']*f['me_k']*8>code_capacity:raise ValueError('actual compact code bank capacity')
                        if f['me_wcs']+f['me_tiles']*(groups//split)*8>scale_capacity:raise ValueError('actual compact scale bank capacity')
                        if f['me_oen'] and f['me_obase']*16+f['me_nout']>plan['required_core']['VM_elements']:
                            raise ValueError('actual ME VM destination capacity')
                        if f['me_xbase']+f['me_k']*split>plan['required_core']['VM_elements']:
                            raise ValueError('actual ME X source capacity')
                    operations.append({'program':name,'pc':pc,'unit':'ME','nout':f['me_nout'],'k':f['me_k'],
                                       'split':split,'native_attention':bool(f['me_wsrc'])})
                elif f['unit']!=I.UNIT_END:raise ValueError('unsupported stage unit')
        results.append({'stage':stage,'kind':kind,'operations':operations})
    if len(results)!=38 or plan['required_core']['VM_elements']>1<<aw:raise ValueError('stage/VM capacity')
    for rank in range(8):
        desc=ISA.decode_descriptor(int((directory/f'head_segments_rank{rank}.hex').read_text(),16))
        if desc['row0']!=rank*18992 or desc['row0']+18992>1<<token_nw:raise ValueError('global head/return token width')
    return {'scope':'38-stage static capacity/source check, not execution or queue performance',
            'parameters':{'SW':sw,'LV':lv,'groups':groups,'provider_NW':provider_nw,'token_NW':token_nw,'AW':aw,'PAW':paw},
            'stages':results,'stage_count':38,'maximum_reduction_elements':4096,
            'required_queue_contract':'One accepted whole-token; whole-op KV seats reserved before SU; native32result beats admitted and actual32VMACK drained; source NFQ4 fetch credits. Runtime stalls/credits require actual composed proof.',
            'remaining_width_contracts':'Typed TAG59 must survive all local/peer returns. Physical views and old untagged517 responses cannot qualify.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    report=check(a.plan)
    try:check(a.plan,lv=4)
    except ValueError as e:report['actual_LV4_capacity_rejected']=str(e)
    else:raise AssertionError('LV4 required-stage overflow escaped preflight')
    a.out.write_text(json.dumps(report,indent=2)+'\n');print('PASS38STAGES; LV4_REJECTED',report['actual_LV4_capacity_rejected'])
