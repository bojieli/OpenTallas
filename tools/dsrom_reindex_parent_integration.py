#!/usr/bin/env python3
"""Minimum fullshape production reindex/mdrop/global-ID stage integration."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_integ_reindex_wf as gate
OPT=0
def main():
 global OPT
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--gold',type=Path,required=True);a=p.parse_args()
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise SystemExit('clean pinned source required')
 a.out.mkdir(parents=True,exist_ok=False)
 a.scratch=a.out
 gate.cmd_prep(a)
 def build(d,lsw,njobs):
  obj=d/f'obj_parent{OPT}_n{njobs}';exe=obj/'Vtb_dsrom_integ_reindex_wf'
  if exe.exists():return exe
  obj.mkdir()
  cmd=[gate.R.verilator(),'--cc','--exe','--build','-j','4','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNOPTFLAT','-Wno-MULTIDRIVEN','--top-module','tb_dsrom_integ_reindex_wf',f'-GOPT_REINDEX_PARENT={OPT}',f'-GLSW={lsw}',f'-GNJOBS={njobs}',*[f'-G{k}={v}' for k,v in gate.PL.items()],f'-GLAT={gate.IDX_ARRAY["latency"]}',f'-GSETTLE={gate.IDX_ARRAY["query_settle"]}','--Mdir',str(obj),*[str(ROOT/f) for f in gate.SRC],str(gate.TB),str(gate.HARNESS),'-CFLAGS','-O1']
  with (obj/'build.log').open('w') as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  return exe
 gate.build=build
 pins=gate.SRC+[str(gate.TB.relative_to(ROOT)),str(gate.HARNESS.relative_to(ROOT)),'tools/dsrom_reindex_parent_integration.py','tools/dsrom_integ_reindex_wf.py','tools/run_abi3_physical.py','tools/orfs_allcorner_spef.py']
 record=dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pins},runs=[],scope='one fullshape reindex stage; actual gather/list binding, existing scorer stand-in and unchanged golden mdrop/globalIDs/top512; no whole array')
 (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
 cases=[(0,'default_off_r3',3,['r3_j0','r3_j1'],3,gate.P0)]+[(1,f'parent_slots_r{r}',3,[f'r{r}_j0',f'r{r}_j1'],r,gate.P0) for r in range(4)]+[(1,'parent_replay',3,['replay_j0'],0,gate.P0+1)]
 for OPT,name,lsw,jobs,rank,pos in cases:
  row=gate.run_one(a.out,name,lsw,jobs,rank,pos);row['OPT_REINDEX_PARENT']=OPT
  record['runs'].append(row);record['pass']=all(x['pass_'] for x in record['runs']);(a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
  print(name,row['pass_'],row['job'],flush=True)
  if not row['pass_']:raise SystemExit(1)
if __name__=='__main__':main()
