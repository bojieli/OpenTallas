#!/usr/bin/env python3
"""Smallest actual h9b/SRAM data baseline and a single enabled-RCD mutant."""
import argparse,json,subprocess,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
from dependency_guard import require_sources
m=require_sources(REPO,REPO,[],'timing833_rcd_source_dependencies.json')
files=[]
for rel in m['shared_repo_files']:
 target=out/Path(rel).name;target.write_bytes((REPO/rel).read_bytes());files.append(target)
leaf=out/'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv';raw=leaf.read_text();needle='.T_RCD(TIMING_833?24:19)'
if raw.count(needle)!=1:raise ValueError('Reviewed enabled-RCD mutant anchor changed')
mut=out/'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b_short_RCD.sv';mut.write_text(raw.replace(needle,'.T_RCD(TIMING_833?19:19)'))
results=[]
for name,source in [('baseline',leaf),('short_RCD',mut)]:
 sources=[str(source),*[str(f)for f in files if f!=leaf],str(HERE/'tb_rcd_guard.sv')]
 obj=out/('obj_'+name)
 with(out/('build_'+name+'.log')).open('w')as log:subprocess.run(['verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','tb_rcd_guard',*sources,'--Mdir',str(obj)],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(obj/'Vtb_rcd_guard')],cwd=out,text=True,capture_output=True);text=r.stdout+r.stderr;(out/(name+'.log')).write_text(text)
 if name=='baseline':assert r.returncode==0 and'PASS REAL_H9B_PROFILE833_ONE_READ'in text,text
 else:assert r.returncode!=0 and'LOCAL_NS_RCD_RD'in text,text
 results.append(dict(name=name,returncode=r.returncode,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),last_lines=text.splitlines()[-4:]))
(out/'control_receipt.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
