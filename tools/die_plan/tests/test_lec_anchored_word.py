from pathlib import Path
import importlib.util,itertools
p=Path(__file__).parents[1] / 'lec.py';sp=importlib.util.spec_from_file_location('lc',p);lc=importlib.util.module_from_spec(sp);sp.loader.exec_module(lc)
def mux(m,s,t,e):return m.AND(m.AND(s,t)^1,m.AND(s^1,e)^1)^1
def seq(regs,fn):
 m=lc.Aig();names=['rst','load']+regs;l={n:m.add_input(n) for n in names};d=fn(m,l)
 a=dict(I=2,L=len(regs),O=0,A=len(m.ands)//2,latches=[d[n] for n in regs],outputs=[],ands=m.ands)
 mp={'input':{i:[(n,0)] for i,n in enumerate(names[:2])},'latch':{i:[('u_dut.'+n+'$_DFF_P_.lecq',0)] for i,n in enumerate(regs)},'output':{}}
 return a,mp
def model(mutant=False):
 def g(m,l):
  out={f'last[{i}]':mux(m,l['rst'],0,mux(m,l['load'],1,l[f'last[{i}]'])) for i in range(3)}
  out['o']=m.XOR(m.XOR(l['last[0]'],l['last[1]']),l['last[2]']);return out
 def t(m,l):return {'last[0]':mux(m,l['rst'],0,mux(m,l['load'],1,l['last[0]'])),'o':l['last[0]']^int(mutant)}
 ga,gm=seq(['last[0]','last[1]','last[2]','o'],g);ta,tm=seq(['last[0]','o'],t);L=lc.Lec(ga,gm,ta,tm)
 k='ff:u_dut.last[0]';nk='ff:u_dut.last#t[0]';L.tp[nk]=L.tp.pop(k);L.tc[nk]=L.tc.pop(k)
 L.matched=sorted(set(L.gp)&set(L.tp));L.gonly=sorted(set(L.gp)-set(L.tp));L.tonly=sorted(set(L.tp)-set(L.gp));L.hyp[('gate',nk)]=('eq','gold',k,0)
 return L
def sat(m):
 for bits in itertools.product((0,1),repeat=m.ni):
  v=[0]+list(bits)
  for a,b in zip(m.ands[::2],m.ands[1::2]):v.append((v[a>>1]^(a&1))&(v[b>>1]^(b&1)))
  if any(v[o>>1]^(o&1) for o in m.outs):return True
 return False
L=model();lc.merged_proposals(L,[]);assert ('gold','ff:u_dut.last[1]') not in L.hyp
for mutant in (False,True):
 L=model(mutant);proposed=lc.anchored_word_proposals(L,[]);assert set(proposed)=={'ff:u_dut.last[1]','ff:u_dut.last[2]'}
 m,_=L.build(with_compare=True,with_hyp=True);assert sat(m)==mutant
L=model();lc.anchored_word_proposals(L,[]);L.hyp[('gold','ff:u_dut.last[1]')]=('eq','gold','ff:u_dut.last[0]',1)
m,_=L.build(with_compare=False,with_hyp=True);assert sat(m)
print('PASS exhaustive anchored-word closure; wrong output and wrong alias mutants rejected')
