"""Qualify generated provider wiring vs its independent manifest; catch a SETTLE mutant.

Ideal clocks qualify source wiring and boot-cycle accounting only. Routed phase,
reset arrival and all die timing gates remain separate.
"""
import json,re,shutil,subprocess,sys
from pathlib import Path
provider,rtl,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=False)
sim=Path(__file__).with_name('sim_start.py')
results={}
for name in ('baseline','settle_mutant'):
    p=provider
    if name=='settle_mutant':
        p=out/'mutant_provider';p.mkdir()
        shutil.copy(provider/'start_stages.json',p/'start_stages.json')
        source=(provider/'start_stages.sv').read_text()
        source,count=re.subn(r'ot_dp_landing_root #\(\.SETTLE\((\d+)\)\)',
                             lambda m:'ot_dp_landing_root #(.SETTLE('+str(int(m[1])+1)+'))',source)
        assert count==1,'one actual root mutant required'
        (p/'start_stages.sv').write_text(source)
    run=subprocess.run([sys.executable,str(sim),str(p),str(rtl),str(out/name)],capture_output=True,text=True)
    if run.returncode:raise RuntimeError(run.stdout+'\n'+run.stderr)
    result=json.loads(run.stdout.strip().splitlines()[-1]);results[name]=result
    clean=result['outputs']==result['sim_outputs'] and result['never_high']==0 and result['diff_hist']=={'0':result['outputs']}
    assert clean==(name=='baseline'),(name,result)
results['verdict']='PASS';results['scope']='ideal-clock source wiring/boot cycles; not physical START phase qualification'
(out/'result.json').write_text(json.dumps(results,indent=1)+'\n')
print(json.dumps(results))
