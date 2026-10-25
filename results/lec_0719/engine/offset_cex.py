exec(open('engine_boundproof.py').read().split('for rnd in range')[0])
import pycryptosat
m,kind=L.build(with_compare=True,with_hyp=True)
name='ff:u_dut.u_lkp.u_e.q_off[1]';i=m.onames.index(name);need=m.cone_inputs(m.outs[i])
s=pycryptosat.Solver()
def cl(xs):
 if 1 not in xs:s.add_clause([-(x>>1) if x&1 else x>>1 for x in xs if x>1])
for k in range(len(m.ands)//2):
 n=2*(m.ni+k+1);x,y=m.ands[2*k:2*k+2];cl([n^1,x]);cl([n^1,y]);cl([n,x^1,y^1])
lit=m.outs[i];sat,model=s.solve(assumptions=[-(lit>>1) if lit&1 else lit>>1]);print('SAT',sat,flush=True)
for v in sorted(need):
 print('input',v,kind.get(v),int(model[v]),flush=True)
vals=[False]*(m.ni+len(m.ands)//2+1)
for v in range(1,m.ni+1):vals[v]=bool(model[v])
def ev(l):return vals[l>>1]^(bool(l&1))
for k in range(len(m.ands)//2):vals[m.ni+k+1]=ev(m.ands[2*k]) and ev(m.ands[2*k+1])
print('gold_D',ev(L.dlit['gold',name]),'gate_D',ev(L.dlit['gate',name]),'miter',ev(m.outs[i]),flush=True)
