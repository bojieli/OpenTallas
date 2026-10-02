#!/usr/bin/env python3
"""Prepare focused primitive sources/input/assertions only; never compile or run HDL."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[1]
BASE='results/rtl/dsrom_bmul_rne_primitive_prepare_20261002'
def sha(b):return hashlib.sha256(b).hexdigest()
def oracle():
    spec=importlib.util.spec_from_file_location('bf_rne_oracle',ROOT/'tools/dsrom_actual_element_numerical_oracle.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
O=oracle()
MUTANTS=('truncation','tie_away','shift_offbyone','negative_zero','old_range','underflow_fault','zero_nonfinite_bypass','refusal_no_fault')
def inputs():
    values=[(0x0080,0x3b80),(0x3380,0x0080),(0x0080,0x3380),(0x0080,0x0080),(0x8080,0x3380),(0x0080,0x3381),(0x0080,0x3400),(0x0080,0x3c00),(0,0x7f80),(0x8000,0xff80),(0x7fc1,0),(0x7f7f,0x7f7f),(0xff7f,0x7f7f),(0,0x8000),(0x8000,0x8000),(0x3f80,0x3f80),(0x3fff,0x3fff),(1,0x3f80),(0x807f,0x3f81),(0x0080,0x3f00)]
    for sh in range(1,25):
        for a in (0x0080,0x0081,0x00ff):
            for m in (0,1,127):
                for sign in (0,0x8000):values.append((a|sign,((127-sh)<<7)|m))
    seed=17
    for _ in range(256):
        seed=(seed*1664525+1013904223)&0xffffffff;a=(seed>>16)&65535
        seed=(seed*1664525+1013904223)&0xffffffff;b=(seed>>16)&65535
        values.append((a,b))
    return values

def expected(a,b):
    if (a&0x7f80)==0x7f80 or (b&0x7f80)==0x7f80:return 0,1
    try:return O.mul(a<<16,b<<16),0
    except ValueError:return 0,1

def encoder_inputs():
    result=[]
    for sh in range(1,25):
        sigs={0x800000,0xffffff,0xfe0100}
        # Nearest-even ties above an even and odd retained LSB, where normalised sig allows it.
        for q in (0x800000>>sh,(0x800000>>sh)+1):
            for delta in (-1,0,1):
                sig=(q<<sh)+(1<<(sh-1))+delta
                if 0x800000<=sig<=0xffffff:sigs.add(sig)
        for sig in sorted(sigs):
            for sign in (0,1):result.append((sign,1-sh,sig))
    for be in (-24,-139):
        for sig in (0x800000,0xffffff):
            for sign in (0,1):result.append((sign,be,sig))
    return result

def input_svh():
    lines=['// INPUT ONLY: raw BF16 operands and generic normalised encoder operands. No expected values.',f'localparam integer PRODUCT_COUNT={len(inputs())};',f'localparam integer ENCODER_COUNT={len(encoder_inputs())};','function automatic [31:0] product_input(input integer i);',' case(i)']
    lines += [f" {i}: product_input=32'h{a:04x}{b:04x};" for i,(a,b) in enumerate(inputs())]
    lines+=[' default:product_input=0;',' endcase','endfunction','function automatic [35:0] encoder_input(input integer i);',' case(i)']
    lines += [f" {i}: encoder_input=36'h{((s<<35)|((be&2047)<<24)|sig):09x};" for i,(s,be,sig) in enumerate(encoder_inputs())]
    return '\n'.join(lines+[' default:encoder_input=0;',' endcase','endfunction',''])
def expected_svh():
    lines=['// ASSERTIONS ONLY. Never used to drive any DUT/encoder input.','function automatic [32:0] product_expected(input integer i);',' case(i)']
    for i,(a,b) in enumerate(inputs()):
        y,e=expected(a,b);lines.append(f" {i}:product_expected=33'h{((e<<32)|y):09x};")
    lines+=[' default:product_expected=0;',' endcase','endfunction','function automatic [31:0] encoder_expected(input integer i);',' case(i)']
    for i,(sign,be,sig) in enumerate(encoder_inputs()):
        y=O.round32((-1 if sign else 1)*O.f32(0x3f800000)*sig*O.pow2(be-150));lines.append(f" {i}:encoder_expected=32'h{y:08x};")
    return '\n'.join(lines+[' default:encoder_expected=0;',' endcase','endfunction',''])
def namespace(s,prefix):return re.sub(r'\bot_[A-Za-z0-9_]+',lambda m:prefix+m[0],s)
def files():
    # Reuse precisely reviewed helper sources; engine source files are untouched.
    spec=importlib.util.spec_from_file_location('numerical_pkg',ROOT/'tools/prepare_dsrom_actual_element_numerical.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep);pkg=prep.package()
    result={n:pkg[n] for n in ('ref_ot_prefix.sv','cand_ot_prefix.sv')}
    original=subprocess.check_output(['git','show','4e38326d6f361bc85e660f48c59c355e2bb95274:rtl/v41rom/ot_v41_bmul2.sv'],cwd=ROOT,text=True)
    fix=(ROOT/'rtl/v41rom/ot_v41_bmul2_rne_prepare.sv').read_text();enc=(ROOT/'rtl/v41rom/ot_v41_bmul_subnormal_rne_prepare.sv').read_text()
    result['ref_ot_v41_bmul2.sv']=namespace(original,'ref_')
    for prefix in ('ref_','cand_'):
        result[prefix+'ot_v41_bmul2_rne_prepare.sv']=namespace(fix,prefix)
        result[prefix+'ot_v41_bmul_subnormal_rne_prepare.sv']=namespace(enc,prefix)
    for name in MUTANTS:
        mutated_fix=fix;mutated_enc=enc
        if name=='truncation':mutated_enc=enc.replace('guard_bit && (sticky_bit || retained[0])',"1'b0")
        if name=='tie_away':mutated_enc=enc.replace('guard_bit && (sticky_bit || retained[0])','guard_bit')
        if name=='shift_offbyone':mutated_enc=enc.replace("11'sd1 - biased_i","11'sd2 - biased_i")
        if name=='negative_zero':mutated_enc=enc.replace("(!in_range || rounded == 24'd0) ? 32'd0 : {sign_i, 7'd0, rounded}","{sign_i, 7'd0, rounded}")
        if name=='old_range':mutated_fix=fix.replace('(GRADUAL_RNE == 0 && s3_be <', '(s3_be <')
        if name=='underflow_fault':mutated_fix=fix.replace('s4_y <= gradual_y;',"begin s4_y <= gradual_y; s4_bad <= 1'b1; end")
        if name=='zero_nonfinite_bypass':mutated_fix=fix.replace('s3_z && !s3_nf','s3_z')
        if name=='refusal_no_fault':mutated_fix=fix.replace("s4_bad <= 1'b1;","s4_bad <= 1'b0;")
        assert (mutated_fix,mutated_enc)!=(fix,enc)
        # Mutants share unchanged reference helpers; mutation is only in copied multiplier/encoder.
        for text,modname in ((mutated_fix,'ot_v41_bmul2_rne_prepare'),(mutated_enc,'ot_v41_bmul_subnormal_rne_prepare')):
            t=namespace(text,'ref_')
            for n in ('ot_v41_bmul2_rne_prepare','ot_v41_bmul_subnormal_rne_prepare'):t=t.replace('ref_'+n,'mut_'+name+'_'+n)
            result['mut_'+name+'_'+modname+'.sv']=t
    for p in ('rtl/test/tb_dsrom_bmul_rne_primitive.sv','rtl/test/dsrom_bmul_rne_primitive_inputs.svh','rtl/test/dsrom_bmul_rne_primitive_expected.svh'):result[Path(p).name]=(ROOT/p).read_text()
    return result

def verify():
    m=json.loads((ROOT/BASE/'model.json').read_text())
    for p,h in m['new_artifact_pins'].items():
        if sha((ROOT/p).read_bytes())!=h:raise ValueError('new pin mismatch '+p)
    for p,h in m['preserved_files_sha256'].items():
        if sha((ROOT/p).read_bytes())!=h or (ROOT/p).read_bytes()!=subprocess.check_output(['git','show',m['preserved_commit']+':'+p],cwd=ROOT):raise ValueError('preservation mismatch '+p)
    if input_svh()!=(ROOT/'rtl/test/dsrom_bmul_rne_primitive_inputs.svh').read_text():raise ValueError('input image changed')
    if expected_svh()!=(ROOT/'rtl/test/dsrom_bmul_rne_primitive_expected.svh').read_text():raise ValueError('assertion table changed')
    if {p:sha(t.encode()) for p,t in files().items()}!=m['generated_files_sha256']:raise ValueError('generated package changed')
    return m

def prepare(out):
    m=verify();out.mkdir(parents=True,exist_ok=False)
    for p,t in files().items():
        with (out/p).open('x') as f:f.write(t)
    receipt=dict(status='PRIMITIVE_PREPARED_NOT_COMPILED',model_sha256=sha((ROOT/BASE/'model.json').read_bytes()),files_sha256=m['generated_files_sha256'],compile_authorized=False,simulate_authorized=False)
    with (out/'preparation.json').open('x') as f:json.dump(receipt,f,indent=2,sort_keys=True);f.write('\n')
    return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.out)
