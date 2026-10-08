#!/usr/bin/env python3
"""Source-preserving default-off direct registered readback successor generator."""
import argparse, hashlib, json
from pathlib import Path
RAW='rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv'
CHECKED='rtl/hbm_accel/qwen/finite_vm_20261005/ot_qwen_checked_vm_bank.sv'
ADAPTER='rtl/hbm_accel/qwen/finite_vm_20261005/ot_qwen_finite_vm_adapter.sv'

def one(s,old,new,n=1):
    assert s.count(old)==n,(old,s.count(old),n)
    return s.replace(old,new)

def generate(root,out):
    out.mkdir(parents=True,exist_ok=True)
    original={p:(root/p).read_text() for p in (RAW,CHECKED,ADAPTER)}
    model=dict(schema='opentallas.qwen-vm-direct-readback.v1',default_enabled=False,added_register_bits=0,added_pipeline_edges=0,raw_bank_or_bits=4*512,raw_bank_or_4input_terms=4*512,original_and_successor_same_register_clock=True,source_capture_epoch_and_ACK_unchanged=True,full16_data_macros=256,check_macros=32,area_delta='Expected zero boolean hardware delta; full implementation not mapped or physically qualified',composed_latency='Existing serialized reference 9-read/28-write minimum service unchanged; selected joined calendar composition applies conditionally',source_sha256={p:hashlib.sha256(s.encode()).hexdigest() for p,s in original.items()},fault_coverage='No new silicon corruption detector; simulation unknown-postverify diagnostic remains separate')
    (out/'prebuild_model.json').write_text(json.dumps(model,indent=2)+'\n')
    raw=original[RAW]
    raw=raw.replace('ot_v41_vm_bank4_macro_pipe_masked_visible_r2','ot_qwen_vm_bank4_direct_readback')
    raw=one(raw,'parameter integer TAG_W = 227','parameter integer DIRECT_READBACK = 0,\n    parameter integer TAG_W = 227',2)
    raw=one(raw,'.DEPTH_GROUPS(DEPTH_GROUPS),.AW(AW),.TAG_W(TAG_W)) u_native (.*);','.DEPTH_GROUPS(DEPTH_GROUPS),.AW(AW),.DIRECT_READBACK(DIRECT_READBACK),.TAG_W(TAG_W)) u_native (.*);')
    old='''            for (integer i=0;i<4;i=i+1)
                rd_out_bank_words[i*512 +:512] <= bank_word[i];'''
    direct='\n'.join(f'                rd_out_bank_words[{i}*512 +:512] <= g_bank[{i}].partial_q[0] | g_bank[{i}].partial_q[1] | g_bank[{i}].partial_q[2] | g_bank[{i}].partial_q[3];' for i in range(4))
    raw=one(raw,old,'            if (DIRECT_READBACK) begin\n'+direct+'\n            end else begin\n'+old+'\n            end')
    chk=original[CHECKED].replace('ot_qwen_checked_vm_bank','ot_qwen_checked_vm_bank_direct_readback').replace('ot_v41_vm_bank4_macro_pipe_masked_visible_r2','ot_qwen_vm_bank4_direct_readback')
    chk=one(chk,'#(parameter integer TAG_W=227)','#(parameter integer DIRECT_READBACK=0, parameter integer TAG_W=227)')
    chk=one(chk,'.MASKED_VISIBLE(1),','.DIRECT_READBACK(DIRECT_READBACK),.MASKED_VISIBLE(1),')
    adapter=original[ADAPTER].replace('ot_qwen_finite_vm_adapter','ot_qwen_finite_vm_adapter_direct_readback').replace('ot_qwen_checked_vm_bank','ot_qwen_checked_vm_bank_direct_readback')
    adapter=one(adapter,'parameter integer ENABLE=0,','parameter integer ENABLE=0,\n    parameter integer DIRECT_READBACK=0,')
    adapter=one(adapter,'#(.TAG_W(TAGW)) u_bank(','#(.DIRECT_READBACK(DIRECT_READBACK),.TAG_W(TAGW)) u_bank(')
    texts={'ot_qwen_vm_bank4_direct_readback.sv':raw,'ot_qwen_checked_vm_bank_direct_readback.sv':chk,'ot_qwen_finite_vm_adapter_direct_readback.sv':adapter}
    for name,s in texts.items():(out/name).write_text(s)
    (out/'generated_sha256.json').write_text(json.dumps({n:hashlib.sha256(s.encode()).hexdigest() for n,s in texts.items()},indent=2)+'\n')
    return texts
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.root,a.out)
