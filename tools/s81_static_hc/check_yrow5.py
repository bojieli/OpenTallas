#!/usr/bin/env python3
"""y_row5 (reduced_seq[8:4] at emit_good) gate: production bench PASS, five real mutants FAIL, fault bench PASS,
and lockstep old-vs-new equivalence of every pre-existing assembler output. Source component only."""
import hashlib,json,pathlib,subprocess,tempfile,time,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/rtl/s81_static_hc_yrow5_1016';OUT.mkdir(parents=True,exist_ok=True)
BASE_REV='289b44007'
RTL='rtl/dsrom_sys/s81_static_hc/'
common=['rtl/ot_fp32_rne_pkg.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/dsrom_sys/s81_ph/ot_s81ph_fp32_add_rne_preexp.sv',
 RTL+'s81_static_hc_reduce.sv',RTL+'s81_static_hc_assemble.sv']
bench=RTL+'test/tb_s81_static_hc.sv';faultbench=RTL+'test/tb_s81_static_hc_faults.sv';eqbench=RTL+'test/tb_s81_static_hc_yrow5_equiv.sv'
inputs=common+[bench,faultbench,eqbench,'tools/s81_static_hc/check_yrow5.py']
res={'scope':'source component only; no native slot, pin, timing or token-rate qualification',
 'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs},'base_rev':BASE_REV,'runs':{}}
want={0:'PASS static HC',1:'word mismatch',2:'row mismatch',3:'y_row5 mismatch',4:'row mismatch',5:'y_row5 mismatch'}
desc={1:'reduce inner tree (p0+p2)+(p1+p3)',2:'assembler word index xor1',3:'row ordinal registered one edge after emit_good',
 4:'row tag registered one edge after emit_good',5:'row ordinal source reduced_seq[7:3] instead of [8:4]'}
def sim(name,top,srcs,params=()):
 with tempfile.TemporaryDirectory(prefix='s81-yrow5-') as tmp:
  b=str(pathlib.Path(tmp)/name)
  subprocess.run(['iverilog','-g2012','-s',top,*params,'-o',b]+srcs,cwd=ROOT,check=True,capture_output=True,text=True)
  t=time.monotonic();r=subprocess.run(['vvp',b],cwd=ROOT,capture_output=True,text=True)
 log=r.stdout+r.stderr;(OUT/f'{name}.log').write_text(log);return r.returncode,log,round(time.monotonic()-t,3)
ok=True
for m,w in want.items():
 rc,log,t=sim(f'mut{m}','tb_s81_static_hc',common+[bench],[f'-Ptb_s81_static_hc.MUT={m}'])
 e=(rc==0 and w in log) if m==0 else (rc!=0 and w in log)
 res['runs'][f'mut{m}']={'returncode':rc,'expected':'PASS' if m==0 else 'FAIL','detected_by':w,'expected_verdict':e,'mutant':desc.get(m),'runtime_seconds':t}
 ok&=e
rc,log,t=sim('faults','tb_s81_static_hc_faults',[RTL+'s81_static_hc_assemble.sv',faultbench])
res['runs']['faults']={'returncode':rc,'expected_verdict':rc==0 and 'PASS assembler' in log};ok&=res['runs']['faults']['expected_verdict']
basesrc=subprocess.run(['git','show',f'{BASE_REV}:{RTL}s81_static_hc_assemble.sv'],cwd=ROOT,check=True,capture_output=True,text=True).stdout
basesrc=basesrc.replace('module s81_static_hc_assemble_clocked','module s81_static_hc_assemble_clocked_base').replace('module s81_static_hc_scalar_assemble(','module s81_static_hc_scalar_assemble_base(').replace(' s81_static_hc_scalar_assemble leaf',' s81_static_hc_scalar_assemble_base leaf')
basesrc=basesrc[:basesrc.index('// Functional compatibility wrapper')]
bp=OUT/'base_assemble_renamed.sv';bp.write_text(basesrc)
res['base_sha256']=hashlib.sha256(basesrc.encode()).hexdigest()
rc,log,t=sim('equiv','tb_s81_static_hc_yrow5_equiv',[str(bp),RTL+'s81_static_hc_assemble.sv',eqbench])
res['runs']['equiv']={'returncode':rc,'expected_verdict':rc==0 and 'PASS y_row5 equivalence' in log,'line':log.strip().splitlines()[-1] if log.strip() else ''}
ok&=res['runs']['equiv']['expected_verdict']
res['verdict']='PASS_SOURCE_ONLY' if ok else 'FAIL'
(OUT/'verdict.json').write_text(json.dumps(res,indent=2,sort_keys=True)+'\n');print(json.dumps(res,indent=2,sort_keys=True))
sys.exit(0 if ok else 1)
