#!/usr/bin/env python3
"""Actual PAGE_AW1/44-macro full-port fault-copy miter. Run heavy cases via ot-run."""
import argparse,pathlib,subprocess,re,json,hashlib,shutil
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
REL='rtl/hbm_accel/generic/peers/';NAMES=['ot_hgi_sfu_programme_store_r10.sv','ot_hgi_sfu_store_stripe_leaf_r10.sv'];GOLD='ec3d375602b3aec19cbe66821386ad6c126c22bb'
def collect(out):
 rows={}
 for m in (0,1):
  s=(out/f'run{m}.log').read_text();mt=re.search(r'RESULT (.*)',s)
  if not mt:raise RuntimeError(f'no measured RESULT in run{m}')
  rows[str(m)]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',mt[1])}
 a,b=rows['0'],rows['1'];ok=(a['mismatches']==0 and a['ctl']>=16 and a['io']>=20 and a['fault_rise']>=2 and a['fault_clear']>=2 and a['hold']>=50 and a['warm']==2 and b['mismatches']>0 and b['transition_bad']>=2)
 return dict(schema='opentallas.hbm.pstore_native_fault_miter.v1',verdict='PASS' if ok else 'FAIL',profile=dict(PAGE_AW=1,NATIVE_FAULT_PIN=1,macro_count=44,output_bits=2282),rows=rows,note='Every reference-defined output bit everyedge incl invalid/sticky-fault cycles; explicit unknown counter. Both real fault rises/clears and stickyholds, 833ps/416.5ps warm reset pulses; no64LOW assumption. Extra-output-edge mutant must fail actual defined fault transitions. Not mapped native guard/LEC/physical qualification.')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--macro',type=pathlib.Path);p.add_argument('--collect-only',action='store_true');a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 if not a.collect_only:
  gold={n:subprocess.check_output(['git','-C',str(ROOT),'show',GOLD+':'+REL+n],text=True) for n in NAMES};mods=[m for t in gold.values() for m in re.findall(r'\bmodule\s+(\w+)',t)];readset={}
  for n,t in gold.items():
   readset[n]=dict(gold_commit=GOLD,gold_sha256=hashlib.sha256(t.encode()).hexdigest(),candidate_sha256=hashlib.sha256((ROOT/REL/n).read_bytes()).hexdigest())
   for m in sorted(mods,key=len,reverse=True):t=re.sub(r'\b'+m+r'\b','old_'+m,t)
   (out/('old_'+n)).write_text(t);shutil.copy2(ROOT/REL/n,out/n)
  shutil.copy2(HERE/'tb.sv',out/'tb.sv');macro=a.macro or ROOT/'physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v';shutil.copy2(macro,out/'macro.v');readset['macro']=dict(path=str(macro),sha256=hashlib.sha256(macro.read_bytes()).hexdigest());(out/'readset.json').write_text(json.dumps(readset,indent=2))
  for m in (0,1):
   cmd=['iverilog','-g2012','-s','tb',f'-Ptb.MUT={m}','-o',f'sim{m}','macro.v',*['old_'+n for n in reversed(NAMES)],*list(reversed(NAMES)),'tb.sv']
   with (out/f'compile{m}.log').open('w') as f:subprocess.run(cmd,cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
   with (out/f'run{m}.log').open('w') as f:subprocess.run(['vvp',f'sim{m}'],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
 d=collect(out);(out/'result.json').write_text(json.dumps(d,indent=2));print(json.dumps(d));return d['verdict']!='PASS'
if __name__=='__main__':raise SystemExit(main())
