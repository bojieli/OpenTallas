#!/usr/bin/env python3
"""Check exact historical physical wrapper text independently of its generator."""
import argparse, hashlib, json, re
from pathlib import Path

def check(wrapper, config, original):
    ports=original['modules']['qfd_sys_face']['ports']
    declarations={n:(d,abs(int(a or 0)-int(b or 0))+1) for d,a,b,n in re.findall(r'^  (input|output) (?:\[(\d+):(\d+)\] )?(\w+);$',wrapper,re.M)}
    assert declarations=={n:(p['direction'],len(p['bits'])) for n,p in ports.items()}
    expected=[];aliases={};binding={}
    for name,p in ports.items():
        if name=='ck':binding[name]=name;continue
        if name=='rst_n':
            expected += [('rst_n','rst_n__ot_rl0'),('rst_n__ot_rl0','rst_n__ot_rl1')]
            binding[name]='rst_n__ot_rl1';continue
        wire=name+'__ot_pr';q=name+'__ot_q';binding[name]=wire
        if p['direction']=='input':expected.append((name,q));aliases[wire]=q
        else:expected.append((wire,q));aliases[name]=q
    actual=[(d,q) for q,d in re.findall(r'  always @\(posedge ck\) (\w+) <= (\w+);',wrapper)]
    assert sorted(actual)==sorted(expected),'historical state/reset equation mismatch'
    assert dict(re.findall(r'^  assign (\w+) = (\w+);$',wrapper,re.M))==aliases
    core=re.findall(r'  qfd_sys_face_control_safe__ot_pr_core u_ot_pr_core \((.*)\);',wrapper)
    assert len(core)==1
    assert dict(re.findall(r'\.(\w+)\((\w+)\)',core[0]))==binding
    assert not re.search(r'\b(initial|negedge|if|else)\b',wrapper),'unexpected boundary state semantics'
    for key,value in [('OT_PIN_REGS','1'),('OT_PIN_REGS_CLOCK','ck'),('OT_PIN_REGS_RESET_PORTS','rst_n'),('OT_RST_LAND','1'),('OT_RST_LAND_STAGES','2')]:
        assert re.findall(r'^export '+key+r'\s*=\s*(\S+)\s*$',config,re.M)==[value]
    return {'status':'PASS','wrapper_sha256':hashlib.sha256(wrapper.encode()).hexdigest(),'config_sha256':hashlib.sha256(config.encode()).hexdigest(),'public_ports':len(ports),'public_bits':sum(len(p['bits']) for p in ports.values()),'input_cycles':1,'output_cycles':1,'synchronous_reset_cycles':2,'reference':'exact historical native12 flow wrapper; no candidate wrapper generator'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('wrapper',type=Path);ap.add_argument('config',type=Path);ap.add_argument('original',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    result=check(a.wrapper.read_text(),a.config.read_text(),json.loads(a.original.read_text()));a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
