"""Compare regenerated split root against old default4 and canonical NQ2 with unchanged split tail cut.
Opaque arithmetic children have identical types, parameters and input connections in the two sides.
"""
from pathlib import Path
import subprocess,json,sys,re
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
old=(src/'old_root.sv').read_text();new=(src/'new_root.sv').read_text();canon=(src/'canonical_root.sv').read_text()
# Golden canonical NQ2 still uses the already-qualified split tail (same as regenerated integration twin).
canon=canon.replace('module ot_hbm_hc_root_static #(','module gold #(').replace('ot_hbm_hc_tail_unit_static #(.MUT_PRE((MUT == 2 && gu == 0) ? 1 : 0)) u_t (','ot_hbm_hc_tail_unit_static_s #(.MUT_PRE((MUT == 2 && gu == 0) ? 1 : 0), .SMUT(0)) u_t (')
rs=[]
for case,nq,gold,mut in [('default4',4,old.replace('module ot_hbm_hc_root_static_s #(','module gold #('),False),('native2',2,canon,False),('native2_mutant',2,canon,True)]:
 gate=new.replace('module ot_hbm_hc_root_static_s #(','module gate #(')
 if mut:gate=gate.replace('ps_q <= qps;',"ps_q <= ~qps;")
 f=out/(case+'.sv');f.write_text(gold+'\n'+gate)
 cfg=f'chparam -set NQ {nq} gold gate;' if case!='default4' else ''
 cmd=f'read_verilog -sv {f}; {cfg} proc; memory; async2sync; opt_clean; equiv_make gold gate equiv; hierarchy -top equiv; equiv_struct; equiv_simple; equiv_induct; equiv_status -assert'
 r=subprocess.run(['yosys','-Q','-T','-p',cmd],capture_output=True,text=True);(out/(case+'.log')).write_text(r.stdout+r.stderr)
 ok=r.returncode!=0 if mut else r.returncode==0;rs.append(dict(case=case,nq=nq,returncode=r.returncode,accepted=ok));print(case,r.returncode,ok,flush=True)
(out/'receipt.json').write_text(json.dumps(dict(checks=rs,pass_all=all(x['accepted'] for x in rs)),indent=2)+'\n')
raise SystemExit(not all(x['accepted'] for x in rs))
