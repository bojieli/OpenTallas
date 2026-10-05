#!/usr/bin/env python3
"""Run real attention control with zero arithmetic stubs. Not numeric evidence."""
import argparse, hashlib, json, subprocess, resource
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def limits():
    n=8*1024**3;resource.setrlimit(resource.RLIMIT_AS,(n,n))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    files=[BASE/'control_stubs.sv',a.root/'rtl/hdc/v41x/ot_hdc_v41x_attn.sv',a.root/'rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv',BASE/'tb_attention_cadence.sv']
    cmd=['iverilog','-g2012','-s','tb_attention_cadence','-o',str(a.out/'cadence.vvp'),*map(str,files)]
    subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=60,preexec_fn=limits)
    rows=[]
    for t,gap in [(128,1),(640,1),(640,4)]:
        run=subprocess.run(['vvp',str(a.out/'cadence.vvp'),f'+rows={t}',f'+gap={gap}'],check=True,capture_output=True,text=True,timeout=60,preexec_fn=limits)
        line=next(x for x in run.stdout.splitlines() if x.startswith('CONTROL_ONLY'))
        rows.append({k:int(v) for k,v in (word.split('=') for word in line.split()[1:])})
    record={'schema':'v41.attention.control-cadence.v1','scope':'Actual fullshape controller/staging, ZERO arithmetic stubs. Synthetic q/kv/p source. Not numeric exactness, connected HBM, softmax, full layer or token.','parameters':{'H':16,'D':512,'TD':32,'NL':4,'TROWS':640},'sources':{str(f):sha(f) for f in files},'compile_command':cmd,'scenarios':rows}
    (a.out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(rows))
if __name__=='__main__':main()
