#!/usr/bin/env python3
"""Actual saved-program binding to the additive fused VM endpoint.

All operand/expected words come unchanged from Rawls load_cases. This module
never evaluates an operator. It emits VM/CR images and command scalars for
actual RTL execution, with original unabsorbed instructions retained.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import numpy as np
from hbm_accel_su_fused_compile import compile_saved
from hbm_accel_su_fused_compile_cases import load_cases


def bits(x):
    return np.asarray(x).view(np.uint32).reshape(-1)


def write_words(path, values):
    Path(path).write_text(''.join(f'{int(x):08x}\n' for x in values))


def bind(cases_path, case_index, candidate_index, out):
    blob,pin=load_cases(cases_path)
    descriptors=compile_saved(cases_path)
    case=blob['cases'][case_index]
    record=descriptors['cases'][case_index]
    group=record['candidates'][candidate_index]
    if not group['selected'] or group['kind']=='index_q':
        raise ValueError('not an executable fusion candidate; retain original ops')
    o=group['operands'];kind=group['kind'];d=o['count']
    kind_no={'hc_norm':0,'q_norm':1,'kv_norm':2,'swiglu':3,'hc_post':4}[kind]
    n={'hc_norm':1024,'q_norm':256,'kv_norm':512,'hc_post':1024}.get(kind,32)
    if kind=='swiglu' and d not in (24,128):
        raise ValueError('actual local activation shape not bound; retain original')
    if kind=='swiglu' and d==128:n=128
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    size=max(max(int(a)+len(v) for a,v in case['init']),
             max(int(a)+len(v) for _,a,v,_ in case['checks']))
    if size>=1<<24:raise ValueError('VM AW24 bounds')
    vm=np.zeros(size,dtype=np.uint32)
    available=np.zeros(size,dtype=np.bool_)
    for a,v in case['init']:
        vm[a:a+len(v)]=bits(v);available[a:a+len(v)]=True
    def read(a,k):
        if a is None or a<0 or a+k>size or not available[a:a+k].all():
            raise ValueError('operand unavailable before real source fence')
        return vm[a:a+k]
    config=np.zeros(32,dtype=np.uint32)
    cmd=np.zeros(6,dtype=np.uint32)
    routed=True
    if kind=='hc_post':
        cmd[:4]=[o['residual_VM_word_address'],o['Y_VM_word_address'],0,o['output_VM_word_address']]
        read(int(cmd[0]),4*d);read(int(cmd[1]),d)
        config[:16]=read(o['comb_VM_word_address'],16)
        config[16:20]=read(o['post_VM_word_address'],4)
    elif kind=='swiglu':
        routed=o['route_weight_VM_word_address'] is not None
        cmd[:4]=[o['gate_VM_word_address'],o['up_VM_word_address'],o['route_weight_VM_word_address'] or 0,o['output_VM_word_address']]
        read(int(cmd[0]),d);read(int(cmd[1]),d)
        if routed:read(int(cmd[2]),1)
        config[22]=o['clip_limit_u32']
    else:
        cmd[:5]=[o.get('hc_VM_word_address',o['input_VM_word_address']),0,0,o['output_VM_word_address'],o['gain_CR_word_address']]
        read(int(cmd[0]),d*(4 if kind=='hc_norm' else 1))
        if kind=='hc_norm':config[16:20]=read(o['pre_VM_word_address'],4)
        config[20]=struct.unpack('<I',struct.pack('<f',d))[0]
        config[21]=o['epsilon_u32']
    cmd[5]=case_index*256+candidate_index
    # Norm-only KV preserves the original retained RoPE operations exactly once.
    # Route shards publish BF16; native global32 quantisation stays downstream.
    quant=False
    checks=[(label,a,w,k) for label,a,w,k in case['checks']
            if int(a)==int(cmd[3]) and len(w)==d*(4 if kind=='hc_post' else 1)]
    if kind=='kv_norm':
        checks=[] # saved expected is AFTER retained RoPE, not norm-only output.
    if not checks and kind!='kv_norm':raise ValueError('no saved matching output check')
    write_words(out/'vm.mem',vm);write_words(out/'cr_lo.mem',bits(case['cr_lo']))
    write_words(out/'cmd.mem',cmd);write_words(out/'cfg.mem',config)
    if checks:write_words(out/'expected.mem',bits(checks[0][2]))
    plan=dict(schema='opentallas.hbm-su-fused-vm-command.v1',cases_sha256=pin,
        case_index=case_index,candidate_index=candidate_index,name=case['name'],kind=kind,
        params=dict(KIND=kind_no,N=n,D=d,RD=0,PUBLISH_QUANT=int(quant),ROUTED=int(routed)),
        memory_words=size,CR_words=len(case['cr_lo']),check_words=len(checks[0][2]) if checks else 0,
        source_available_before_command=True,original_op_indexes=group['original_op_indexes'],
        original_ops=record['original_ops'],retained_op_indexes=record['retained_op_indexes'],
        original_order_authoritative=True,VM_command_words=cmd.tolist(),
        expected_source='saved checks; KV after original retained RoPE only',
        quantization='unchanged downstream producer/ownership',adopted=False)
    plan['files_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.mem')}
    (out/'command.json').write_text(json.dumps(plan,indent=2)+'\n')
    return plan


def bind_finite_norm(cases_path, case_index, candidate_index, out):
    """Bind actual saved norm bits to the selected finite sector provider.

    This is a component command, never a replacement original program or
    fabricated schedule/retirement. The enclosing caller retains native RoPE
    and quantisation and must supply an actual drained exclusive route lease.
    """
    from gpu_sys.mem_image import write_images
    out=Path(out)
    plan=bind(cases_path,case_index,candidate_index,out)
    if plan['kind'] not in ('q_norm','kv_norm'):
        raise ValueError('finite norm adapter does not implement this family')
    if not plan['check_words']:
        raise ValueError('KV saved check requires original retained RoPE; enclosing native binding still required')
    # Initial memory contains only init/CR source bits. expected.mem is never
    # added to the provider image, including output/intermediate regions.
    from hbm_accel_su_fused_program import load_hex
    vm=load_hex(out/'vm.mem');cr=load_hex(out/'cr_lo.mem')
    write_images({0:vm.astype('<u4').tobytes(),0x100000:cr.astype('<u4').tobytes()},
                 2,32768,out,prefix='memory')
    cmd=load_hex(out/'cmd.mem');cfg=load_hex(out/'cfg.mem')
    write_words(out/'finite_cmd.mem',np.concatenate((cmd,cfg[20:22])))
    plan.update(schema='opentallas.hbm-su-finite-norm-command.v1',
        provider=dict(source='rtl/gpu_sys/ot_gpu_mreq_cdc.sv -> ot_gpu_memsys.sv',
                      AW=3,NC=1,NS=2,NPC=2,MEM_WORDS=32768,USE_W2=0,
                      vm_byte_base=0,cr_byte_base=0x100000),
        parent_program_integration=False,original_schedule_replaced=False,
        retained_RoPE_and_quant='original runtime, not executed by this component',
        actual_parent_lease_bound=False,SS60_FF25_qualified=False)
    plan['files_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.mem')}
    plan['files_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('memory_*.hex')})
    (out/'finite_command.json').write_text(json.dumps(plan,indent=2)+'\n')
    return plan


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases',type=Path,required=True)
    ap.add_argument('--case-index',type=int,required=True)
    ap.add_argument('--candidate-index',type=int,default=0)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(bind(a.cases,a.case_index,a.candidate_index,a.out),indent=2))
