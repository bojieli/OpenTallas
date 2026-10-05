#!/usr/bin/env python3
"""Run cached checkpoint Qwen graph with post-execution independent comparison.

Software functional evidence only. Each successful L0 is a prefix receipt;
the same execution then continues without recomputing or injecting layers.
"""
import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
import numpy as np
import torch
from qwen_hbm_complete_program import compile_program,coverage,ROOT
from qwen_hbm_complete_executor import CheckpointWeights,SoftwareGPUProvider,execute
from qwen_hbm_complete_reference import PostExecutionReference

def write_json(path,value):
    temporary=path.with_suffix(path.suffix+'.new')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    os.replace(temporary,path)

def run(snapshot,out,*,token=9707,steps=2,layers=36):
    if not 1<=steps<=2 or not 1<=layers<=36:raise ValueError('bounded token/layer scope')
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    program=compile_program();out.mkdir(parents=True,exist_ok=False)
    weights=CheckpointWeights(program,snapshot);provider=SoftwareGPUProvider(program,weights)
    reference=PostExecutionReference(program,weights);progress=[];receipts=[];started=time.time()
    write_json(out/'program_scope.json',dict(program_sha256=hashlib.sha256((json.dumps(program,indent=2)+'\n').encode()).hexdigest(),coverage=coverage(program),layers_requested=layers,steps_requested=steps,initial_token=token,software_is_DUT=False))
    try:
        for position in range(steps):
            if position and layers!=36:raise ValueError('prefix has no produced autoregressive token')
            reference.start_token(token,position)
            def observe(op,values):
                for name,value in zip(op['outputs'],values):
                    array=np.asarray(value) if not isinstance(value,dict) else None
                    entry=dict(position=position,instruction=op['id'],opcode=op['opcode'],register=name)
                    if array is not None and array.dtype.kind in 'fiu':
                        entry.update(shape=list(array.shape),sha256=hashlib.sha256(array.tobytes()).hexdigest())
                    progress.append(entry)
                    layer=re.fullmatch(r'L(\d+)\.X',name)
                    if layer:
                        index=int(layer.group(1));np.save(out/f'token{position}_L{index:02d}.npy',value,allow_pickle=False)
                        reference.layer(index,np.asarray(value).copy())
                        if provider.memory.leases or provider.memory.pending:raise ValueError('layer retains software consumer/write leases')
                        receipt=dict(position=position,layer=index,instructions_retired=op['id']+1,
                                     exactness=reference.comparisons[-1],persistent_publications=len(provider.memory.published),
                                     reader_leases_outstanding=len(provider.memory.leases),elapsed_software_seconds=time.time()-started,
                                     fullshape_checkpoint_prefix=True,actual_RTL_executed=False,token_cycles=None)
                        write_json(out/f'token{position}_L{index:02d}_receipt.json',receipt)
                        print(json.dumps(dict(event='LAYER_EXACT_PREFIX',**receipt)),flush=True)
                    elif name=='head.norm':reference.final_norm(value)
                    elif re.fullmatch(r'head\.d[01]\.scaled',name):
                        np.save(out/f'token{position}_{name}.npy',value,allow_pickle=False)
                        reference.head(int(name[6]),np.asarray(value).copy())
            result=execute(program,provider,token,position,observer=observe,stop_after_layer=layers-1 if layers<36 else None)
            if layers==36 and result['next_token']!=reference.next_token:raise ValueError('independent final argmax mismatch')
            result.update(input_token=token,post_execution_comparisons=list(reference.comparisons),
                          reference_scope='Independent Torch shipped arithmetic, private activations and KV, common admitted weight recipe; no golden injection',
                          actual_hardware_memory_provider=False,hardware_consumer_leases_qualified=False)
            write_json(out/f'token{position}_execution.json',result);receipts.append(result)
            token=result['next_token']
        terminal=dict(status='CHECKPOINT_SOFTWARE_COMPLETE' if layers==36 else 'CHECKPOINT_SOFTWARE_PREFIX_COMPLETE',
                      tokens_completed=len(receipts),layers_per_token=layers,head_executed=layers==36,
                      next_token=token,all_recorded_bit_mismatches=sum(x['bit_mismatches'] for x in reference.comparisons),
                      fullshape_checkpoint_functional=True,actual_RTL_executed=False,fulltoken_RTL=False,
                      token_cycles=None,token_rate=None,elapsed_software_seconds=time.time()-started)
    except BaseException as error:
        terminal=dict(status='CHECKPOINT_SOFTWARE_FAILED',error_type=type(error).__name__,error=str(error),
                      actual_RTL_executed=False,fulltoken_RTL=False,token_cycles=None,token_rate=None)
        write_json(out/'failure.json',terminal)
        raise
    finally:
        write_json(out/'checkpoint_reader_provenance.json',weights.provenance())
        write_json(out/'post_execution_comparisons.json',reference.comparisons)
        write_json(out/'instruction_output_hashes.json',progress)
    write_json(out/'terminal.json',terminal)
    print(json.dumps(terminal),flush=True)
    return terminal

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--token',type=int,default=9707);parser.add_argument('--steps',type=int,default=2)
    parser.add_argument('--layers',type=int,default=36);parser.add_argument('--admission-gate',type=Path)
    args=parser.parse_args()
    if args.admission_gate:
        deadline=time.monotonic()+60
        while not args.admission_gate.exists():
            if time.monotonic()>deadline:raise RuntimeError('missing authoritative admission')
            time.sleep(.1)
        gate=json.loads(args.admission_gate.read_text())
        start=Path('/proc/self/stat').read_text().split(') ',1)[1].split()[19]
        if gate['pid']!=os.getpid() or str(gate['start_ticks'])!=start or gate['cwd']!=str(Path.cwd()):raise RuntimeError('admission identity mismatch')
    run(args.snapshot,args.out,token=args.token,steps=args.steps,layers=args.layers)
