from pathlib import Path
import os,subprocess,json
import argparse,shutil
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--production-case',action='store_true');args=ap.parse_args()
repo=Path(__file__).resolve().parents[4];w=args.out.resolve();w.mkdir(parents=True,exist_ok=True);os.chdir(w)
v=shutil.which('verilator');assert v,'verilator executable required on PATH'
bench=repo/'rtl/test/meso/writer_calendar_tree'
results=[]
cases=[(326,1,False)] if args.production_case else [(514,1,False),(326,0,False),(133,1,False),(514,1,True)]
for width,neg,mut in cases:
 name=f'native_w{width}_n{neg}_mut{int(mut)}';obj='obj_'+name
 assert not Path(obj).exists(),'preserve results, use fresh objdir'
 with open(name+'.log','w') as f:
  cmd=[v,'--cc','--exe','--top-module','wct_native_top','-Wno-fatal','--Mdir',obj,f'-GW={width}',f'-GWNEG={neg}']
  if mut:cmd+=['+define+OT_MESO_MUTANT_WCT_LOOKAHEAD']
  cmd+=[str(repo/'rtl/common/ot_meso_fifo.sv'),str(repo/'rtl/common/ot_dp_clk_landing.sv'),str(bench/'wct_native_top.sv'),str(bench/'wct_native_main.cpp')]
  subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['make','-C',obj,'-f','Vwct_native_top.mk','-j1'],stdout=f,stderr=subprocess.STDOUT,check=True)
  for phase in ([137] if mut else [0,137,631]):
   r=subprocess.run([obj+'/Vwct_native_top',str(phase)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);f.write(r.stdout)
   ok=r.returncode==1 and 'DATA_FAIL' in r.stdout if mut else r.returncode==0
   rec={'W':width,'WNEG':neg,'phase':phase,'mutant':mut,'rc':r.returncode,'pass':ok,'output':r.stdout.strip()};results.append(rec);print(rec,flush=True)
   Path('writer_native_proof_results.json').write_text(json.dumps(results,indent=2)+'\n')
   assert ok
assert len(results)==(3 if args.production_case else 10) and all(r['pass'] for r in results)
