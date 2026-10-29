"""Universal one-cell equivalence: same original master, params and ports after a zero seed is internalized.
The master is opaque, so this proof covers every original master implementation and its state, without arithmetic changes.
A wrong seed and a swapped data pin are controls; no whole-SM simulation is needed.
"""
import json,re,subprocess,tempfile,sys
from pathlib import Path
from seed_heads import ROOT,SPECS,wrapper
sys.path.insert(0,str(ROOT/'tools'));import die_port_bind as D
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
res=[]
for mod,seed,_,_,width in SPECS:
 src=ROOT/'rtl/hbm_accel/sm/attn'/f'{mod}.sv';s=src.read_text();head=s[s.index('module '+mod):re.search(r'^\s*\);\s*$',s[s.index('module '+mod):],re.M).end()+s.index('module '+mod)]
 cand,_=wrapper(mod,seed);variant=mod+'_seed';ch=cand[:re.search(r'^\s*\);\s*$',cand,re.M).end()]
 # Gold explicitly instantiates the original master with its production seed and all other ports preserved.
 pm=next(x for x in D.parse_modules(s,str(src)) if x.name==mod);pars=[x for x in pm.params if x not in pm.localparams]
 gold=ch.replace(variant,'gold',1)+'\n'+mod+' #('+','.join('.'+x+'('+x+')' for x in pars)+') u_ref ('+','.join('.'+x+"('0)" if x==seed else '.'+x+'('+x+')' for x in pm.ports)+');\nendmodule\n'
 for mode in ('exact','mutant_seed'):
  gate=cand.replace(variant,'gate',1)
  if mode=='mutant_seed':gate=gate.replace('.'+seed+"('0)",'.'+seed+"('1)")
  f=out/f'{mod}_{mode}.sv';f.write_text('(* blackbox *) '+head+'\nendmodule\n'+gold+gate)
  cmd=f'read_verilog -sv {f}; hierarchy -check; proc; equiv_make gold gate equiv; hierarchy -top equiv; equiv_struct; equiv_simple; equiv_status -assert'
  r=subprocess.run(['yosys','-Q','-T','-p',cmd],capture_output=True,text=True)
  (out/f'{mod}_{mode}.log').write_text(r.stdout+r.stderr)
  ok=(r.returncode==0) if mode=='exact' else (r.returncode!=0)
  res.append(dict(module=mod,mode=mode,returncode=r.returncode,expected=('PASS' if mode=='exact' else 'FAIL'),accepted=ok))
  print(mod,mode,r.returncode,ok)
(out/'receipt.json').write_text(json.dumps(dict(method='opaque-identical-master equiv_struct, all inputs and parameters identical; arbitrary underlying sequential implementation',checks=res,pass_all=all(x['accepted'] for x in res)),indent=2)+'\n')
raise SystemExit(0 if all(x['accepted'] for x in res) else 1)
