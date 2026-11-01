import json,re,itertools
from pathlib import Path
from sympy import Symbol,And,Or,Not,Xor,false
p=Path(__file__).with_name("tail_cone.json");d=json.load(open(p));v={};sym={}
for n,(cell,name,ports) in d['leaves'].items():
 assert cell=='DFFHQNx1_ASAP7_75t_R'
 k=name.lstrip('\\').split('$_')[0];sym[k]=Symbol(k);v[n]=Not(sym[k]) # lib IQN/negative output; canonical register stores D
for n,(cell,name,ports) in d['ops']:
 c=cell.split('x')[0];ins={k:v[w] for k,w in ports.items() if k not in ('Y','QN','Q','CLK')}
 if c=='BUF':x=ins['A']
 elif c=='INV':x=Not(ins['A'])
 elif c.startswith('AND'):x=And(*ins.values())
 elif c.startswith('OR'):x=Or(*ins.values())
 elif c=='AO21':x=Or(And(ins['A1'],ins['A2']),ins['B'])
 else:raise ValueError(cell)
 v[n]=x
base='u_bound.u_core.u_dec.u_syn.';bm=base+'g_bm[0].u_bm.'
zd=And(*[Not(sym[bm+f'dz[3][{i}]']) for i in range(10)])
zs=And(*[Not(sym[base+f'S_q[{i}]']) for i in range(10)])
k=sym[bm+'kc[3][5]'];ld=sym[base+'ldr[0][3]'];q=sym[bm+'th[45][1]']
Z,S=Symbol('D_zero'),Symbol('S_zero')
gate=v[d['root']].xreplace({zd:Z})
gate=gate.replace(lambda x: x.func == And and set(zs.args) <= set(x.args), lambda x: And(S, *[a for a in x.args if a not in zs.args]))
assert gate.free_symbols=={Z,S,k,ld,q},gate
# Original RTL bit45[0]: upd=(ld ? !S_zero : !D_zero && !K5), init45[0]=1.
gold=And(Not(Or(And(ld,Not(S)),And(Not(ld),Not(Z),Not(k)))),Or(ld,q))
wrong=gold.xreplace({q:false})
errors=[];mutants=[]
for bits in itertools.product((False,True),repeat=5):
 a=dict(zip((Z,S,k,ld,q),bits))
 if bool(gate.subs(a)) != bool(gold.subs(a)):errors.append(bits)
 if bool(gate.subs(a)) != bool(wrong.subs(a)):mutants.append(bits)
print('terminal narrowed-cell relation: all32 cases',len(errors),'mismatches; wrong zero-bit pairing mutant',len(mutants),'differences')
assert not errors and mutants
out=dict(source=d['netlist'],gate_cell='th[45][1]',gold_register='th[5][50] = source th[45][0]',gate_expr=str(gate),gold_expr=str(gold),aggregate_cases=32,mismatches=len(errors),wrong_bit_mutant_differences=len(mutants))
Path(__file__).with_name("tail_relation.json").write_text(json.dumps(out,indent=2)+'\n')
