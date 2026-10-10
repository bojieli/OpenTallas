#!/usr/bin/env python3
"""Minimum real-width link: actual registered relay round trip, stalls, exact flits."""
import argparse, ast, hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SRC=['rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv','rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv','rtl/dsrom_sys/mtp/tb_mtp_link_rtt.sv']
def run(out,f,r,sel,enable,mutant=False,stress=1,depth=0):
    name=f'f{f}_r{r}_s{sel}_e{enable}'+('_short_history' if mutant else '')+('_fullrate' if not stress else '')+(f'_depth{depth}' if depth else '')
    exe=out/(name+'.vvp');cmd=['iverilog','-g2012','-s','tb_mtp_link_rtt']
    for k,v in dict(F=f,R=r,SEL=sel,ENABLE=enable,STRESS=stress,DEPTH=depth).items():cmd += [f'-Ptb_mtp_link_rtt.{k}={v}']
    if mutant:cmd+=['-DOT_MTP_NEG_SHORT_RTT']
    cmd+=['-o',str(exe)]+SRC
    c=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    (out/(name+'.compile.log')).write_text(c.stdout+c.stderr)
    if c.returncode:raise RuntimeError('compile failed '+name)
    p=subprocess.run(['vvp',str(exe)],cwd=ROOT,capture_output=True,text=True)
    (out/(name+'.log')).write_text(p.stdout+p.stderr);exe.unlink()
    expected=p.returncode==1 and 'LINK_REG overflow' in p.stdout if mutant else p.returncode==0 and 'PASS RTT_LINK' in p.stdout
    counts={k:int(v) for k,v in re.findall(r'(W|F|R|H|D|SEL|ENABLE|STRESS|sent|received|cycles|stalls|max_outstanding|first_latency)=(\d+)',p.stdout)}
    if not mutant:expected=expected and counts.get('sent')==1200 and counts.get('received')==1200 and counts.get('first_latency')==f+2
    return dict(name=name,expect='FAIL' if mutant else 'PASS',observed_rc=p.returncode,gate_pass=expected,measurement=counts)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    # Evaluate only the named unified model function; avoids importing unrelated model datasets.
    tree=ast.parse((ROOT/'tools/uarch_model.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dsrom_mtp_grant_rtt_model')
    ns={'DFF_UM2':.2916};exec(compile(ast.Module(body=[node],type_ignores=[]),'unified_model','exec'),ns)
    pairs=[(0,0),(5,5),(9,9),(5,9),(9,5)]
    models=[ns[node.name](f,r) for f,r in pairs];(a.out/'model.json').write_text(json.dumps(models,indent=2)+'\n')
    rows=[run(a.out,f,r,s,1) for f,r in pairs for s in (0,1)]
    rows += [run(a.out,f,r,s,1,stress=0) for f,r in pairs for s in (0,1)]
    rows += [run(a.out,0,0,s,0) for s in (0,1)]
    rows += [run(a.out,f,r,s,1,depth=4) for f,r in [(5,5),(9,9)] for s in (0,1)]
    rows += [run(a.out,f,r,s,1,True) for f,r in pairs for s in (0,1)]
    record=dict(status='PASS' if all(r['gate_pass'] for r in rows) else 'FAIL',adopted=False,physical_closed=False,
      scope='Minimum 512-bit production sender / successor receiver with registered forward/reverse relays, backpressure; no whole-system claim',
      sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SRC},models=models,runs=rows)
    (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    print(record['status'],'RTT_LINK',len(rows),'cases',sum(r['measurement'].get('received',0) for r in rows),'exact flits')
    if record['status']!='PASS':sys.exit(1)
if __name__=='__main__':main()
