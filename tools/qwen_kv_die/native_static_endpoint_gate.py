#!/usr/bin/env python3
"""Small actual controller/descriptor/codec gate; service face is external stimulus.

This gate makes no arithmetic, whole-layer or whole-token native claim.
"""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from compile_native_endpoint import compile_programme
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/qwen_sys/split_20261014/'+s+'.sv' for s in (
 'qkd_native_attention_programme','qkd_native_attention_static_ctl','qkd_native_attention_record','qkd_native59_command_guard','qkd_native59_descriptor_producer')]
SOURCES+=['rtl/test/qwen_split/tb_native_attention_static_ctl.sv']

def main():
    results=[]
    with tempfile.TemporaryDirectory(prefix='qkd-native-endpoint-') as td:
        for mut,mode,passed in [(0,mode,True) for mode in range(9)]+[(1,1,False)]:
            binary=str(Path(td)/f'ctl{mut}')
            subprocess.run(['iverilog','-g2012','-s','tb_native_attention_static_ctl',
                            f'-Ptb_native_attention_static_ctl.MUT={mut}','-o',binary,
                            *[str(ROOT/s) for s in SOURCES]],check=True)
            r=subprocess.run(['vvp',binary,f'+MODE={mode}'],text=True,capture_output=True)
            if (r.returncode==0)!=passed:
                raise RuntimeError(f'unexpected gate outcome mut{mut} mode{mode}: '+r.stdout+r.stderr)
            results.append(dict(mutant=mut,mode=mode,returncode=r.returncode,output=r.stdout.strip()))
    programmes=[]
    for T in (1,1000,3000,4096,6144,8192):
        for layer in range(36):
            p=compile_programme(17,19,T-1,layer,4)
            assert p['result_last']+1==p['result_done']==p['reserved_idle']
            assert p['status']==p['result_done']+1
            assert int(p['tag_hex'],16)>>37&63==layer+1
            programmes.append((T,layer,p['service_edges']))
    for args in [(17,19,8192,0,4),(17,151936,0,0,4),(17,19,0,36,4),(17,19,0,0,0)]:
        try:compile_programme(*args)
        except ValueError:pass
        else:raise RuntimeError('invalid programme accepted')
    receipt=dict(scope='actual descriptor/controller/codec component with declared external service stimulus',
                 native_full_layer=False,native_full_token=False,
                 results=results,compiled_programmes=len(programmes),
                 service_8192_edges=compile_programme(17,19,8191,0,4)['service_edges'],
                 sources={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES})
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
