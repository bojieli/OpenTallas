#!/usr/bin/env python3
"""Run the selected 100-SRAM PSlice boundary miter (heavy: invoke through ot-run).

Gold reads the ACTUAL GEN recipe: pgcol@c5e7639, programme/relay@d34578d6f.
Compare every reference-defined output bit, including valid=0. Undefined bits are
counted explicitly. The full-core phase and small actual-head cfg-phase controls
must both fail; no production source or timing contract is adopted by this unit.
"""
import argparse,hashlib,json,pathlib,re,subprocess,shutil
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REL='rtl/hbm_accel/generic/adapters/static_su/programme/'
GOLD={REL+'ot_hbm_su_programme_pgcol.sv':'c5e7639295724dcf76eb43a27ae588732f7cbc74',REL+'ot_hbm_su_programme.sv':'d34578d6f','rtl/lib/ot_rst_relay.sv':'d34578d6f'}
def execute(cmd,log,cwd):
 with log.open('w') as f:subprocess.run(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,check=True)
def collect(out):
 rows={}
 for name in ('run0','run1','head_run0','head_run1'):
  t=(out/(name+'.log')).read_text();m=re.search(r'(?:HEAD_)?RESULT (.*)',t)
  if not m:raise RuntimeError(f'no measured verdict in {name}')
  row={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])};rows[name]=row
 ok=(rows['run0']['mismatches']==0 and rows['run0']['valid']>40 and rows['run0']['nonzero']>0 and rows['run0']['warm']==2 and rows['run1']['mismatches']>0 and rows['head_run0']['mismatches']==0 and rows['head_run0']['cwe_mismatches']==0 and rows['head_run1']['mismatches']>0 and rows['head_run1']['cwe_mismatches']>0)
 return dict(schema='opentallas.hbm.pslice_native_boundary_miter.v1',verdict='PASS' if ok else 'FAIL',profile=dict(SB=2470,NCX=1,NATIVE_PINS=1,macro_count=100),rows=rows,note='All reference-defined bits each edge including valid0; unknown counts explicit. Two short warm resets, no64LOW assumption. This source unit is not mapped gate, LEC, timing, or physical qualification.')
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=pathlib.Path);ap.add_argument('--macro',type=pathlib.Path);ap.add_argument('--collect-only',action='store_true');a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 if not a.collect_only:
  gold={p:subprocess.check_output(['git','-C',str(ROOT),'show',ref+':'+p],text=True) for p,ref in GOLD.items()};mods=[m for p,t in gold.items() if p.endswith('programme.sv') or p.endswith('pgcol.sv') for m in re.findall(r'\bmodule\s+(\w+)',t)]
  hashes={}
  for p,t in gold.items():
   hashes[p]=dict(commit=GOLD[p],sha256=hashlib.sha256(t.encode()).hexdigest())
   if p.endswith('ot_rst_relay.sv'):(out/'ot_rst_relay.sv').write_text(t);continue
   for m in sorted(mods,key=len,reverse=True):t=re.sub(r'\b'+m+r'\b','old_'+m,t)
   (out/('old_'+pathlib.Path(p).name)).write_text(t);shutil.copy2(ROOT/p,out/pathlib.Path(p).name)
  for n in ('tb.sv','tb_head.sv'):shutil.copy2(HERE/n,out/n)
  macro=a.macro or ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v';shutil.copy2(macro,out/'macro.v');hashes['macro']=dict(path=str(macro),sha256=hashlib.sha256(macro.read_bytes()).hexdigest());(out/'gold_readset.json').write_text(json.dumps(hashes,indent=2))
  src=['ot_rst_relay.sv','macro.v','old_ot_hbm_su_programme.sv','old_ot_hbm_su_programme_pgcol.sv','ot_hbm_su_programme.sv','ot_hbm_su_programme_pgcol.sv']
  for top,prefix,tb in [('tb','run','tb.sv'),('tb_head','head_run','tb_head.sv')]:
   for m in (0,1):
    exe=top+str(m);execute(['iverilog','-g2012','-s',top,f'-P{top}.MUT={m}','-o',exe,*src,tb],out/(exe+'_compile.log'),out);execute(['vvp',exe],out/(prefix+str(m)+'.log'),out)
 d=collect(out);(out/'result.json').write_text(json.dumps(d,indent=2));print(json.dumps(d));return d['verdict']!='PASS'
if __name__=='__main__':raise SystemExit(main())
