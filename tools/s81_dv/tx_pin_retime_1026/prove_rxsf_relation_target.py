import importlib.util,json,sys
from pathlib import Path
p=Path('/work');out=Path('/diag/out');out.mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('oldlec',p/'lec.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
def tup(a):return tuple(tup(v) for v in a) if isinstance(a,list) else a
for inv in (0,1):
 l=x.Lec(x.read_aig(p/'lec/gold.aig'),x.read_map(p/'lec/gold.map'),x.read_aig(p/'lec/gate.aig'),x.read_map(p/'lec/gate.map'))
 l.hyp={(a,b):tup(c) for a,b,c in json.loads((p/'lec/hyp.json').read_text())}
 key='ff:u_dut.u_f.u_exp.g_h[6].u_h.s3_pf[26]';rep='ff:u_dut.u_f.u_exp.g_h[6].u_h.s3_neg'
 l.hyp['both',key]=('eq','gold',rep,inv)
 m,_=l.build(); chosen=[i for i,n in enumerate(m.onames) if n.startswith('ff:u_dut.u_f.u_exp.g_h[6].u_h.y[') or n in ['hyp:both:'+key,'hyp:bothg:'+key]]; m.outs=[m.outs[i] for i in chosen];m.onames=[m.onames[i] for i in chosen];log=[];st=x.prove(m,out,10000,log,tag='right' if inv==0 else 'wrong')
 (out/('right.log' if inv==0 else 'wrong.log')).write_text('\n'.join(log))
 bad={k:v for k,v in st.items() if v!='proved'}
 print('inv',inv,'obligations',len(st),'failed',len(bad),bad,flush=True)
 (out/('right.json' if inv==0 else 'wrong.json')).write_text(json.dumps(dict(inv=inv,obligations=len(st),failed=bad),indent=2))
 if inv==0 and bad:raise SystemExit('right relation not proven')
 if inv==1 and not bad:raise SystemExit('wrong relation escaped')
