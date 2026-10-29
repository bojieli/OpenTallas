"""Independent RTL wiring miter: unchanged leaves have shared arbitrary outputs; all leaf inputs are obligations.

This proves zero-cycle wiring replacement compositionally, including every clock/reset input.
It does not replace the reused leaves' arithmetic, sequential, memory, or physical qualifications.
"""
import json,pathlib,re
import canonical_graph as C
D=pathlib.Path(__file__).resolve().parent;O=D/'wiring_proof';O.mkdir(exist_ok=True)
REC=json.load(open(D/'canonical/mapping.json'))['canonical_masters']
PAT=re.compile(r'^    (\w+)(?: (#[^\n]*))? (u_u_(exp|rsq|head|rcp|lrly)\d+) \(\n(.*?)^    \);',re.M|re.S)
def owner(atom,outputs):
 n,b=atom
 if n=='O':n=outputs[b]['name']
 m=re.match(r'w_u_(exp|rsq|head|rcp|lrly)(?:LANE|\d+)_',n)
 return m[1] if m else None
z=C.canonical(REC[0]['actual_native_masters'][0]);r=json.load(open(C.P/'cuts'/REC[0]['actual_native_masters'][0]/'cut.json'))
PORTS={};SYMS=[];MON=[];defs=[]
for c in z['cells']:
 role=c['role'];PORTS[role]={}
 for p,bits in sorted(c['ports'].items()):
  own={owner(q,r['outputs']) for q in bits};own.discard(None)
  assert not (role in own and own!={role}), (role,p,own)
  dr='output' if own=={role} else 'input';PORTS[role][p]=(dr,len(bits))
  (SYMS if dr=='output' else MON).append((role,p,len(bits)))
 fields=[f'{dr} wire [{w-1}:0] {p}' for p,(dr,w) in sorted(PORTS[role].items())]
 fields += [f'input wire [{w-1}:0] sym_{p}' for rr,p,w in SYMS if rr==role]
 defs.append('module probe_'+role+' #(parameter MEMORY_ALIGNMENT=0, MEMORY_READ_EXTRA=0)('+', '.join(fields)+');\n'+''.join(f'assign {p}=sym_{p};\n' for rr,p,w in SYMS if rr==role)+'endmodule\n')
SMW=sum(w for _,_,w in MON)
def instrument(s,name,mutant=False):
 old=s[s.index('module '):].split(');',1)[1];body=old[:old.rindex('endmodule')]
 hi=int(re.search(r'output wire \[(\d+):0\] c_o',s)[1]);co=hi+1
 if mutant:
  body=re.sub(r'\bc_o\b','raw_o',body);body='wire ['+str(hi)+':0] raw_o;\n'+body+'\nassign c_o={raw_o['+str(hi)+':2],raw_o[0],raw_o[1]};\n'
 mons={};count=0
 def cell(m):
  nonlocal count
  mod,params,inst,role,ports=m.groups();assert re.sub(r'\s+','',params or '')==next(x['params'] for x in z['cells'] if x['role']==role)
  args=dict(re.findall(r'\.(\w+)\(([^()]+)\)',ports));assert set(args)==set(PORTS[role]),(name,role,set(args)^set(PORTS[role]))
  for p,(dr,w) in PORTS[role].items():
   if dr=='input':mons[(role,p)]=args[p]
  injected=ports.rstrip().rstrip(',')+',\n'+',\n'.join(f'        .sym_{p}(sym_{role}_{p})' for rr,p,w in SYMS if rr==role)
  count+=1;return '    probe_'+role+((' '+params) if params else '')+' '+inst+' (\n'+injected+'\n    );'
 body=PAT.sub(cell,body);assert count==5,(name,count)
 fields=['input wire clk','input wire rst_n','input wire [759:0] c_i',f'output wire [{hi}:0] c_o']+[f'input wire [{w-1}:0] sym_{rr}_{p}' for rr,p,w in SYMS]+[f'output wire [{SMW-1}:0] monitors']
 monitor='{'+', '.join(mons[(rr,p)] for rr,p,w in reversed(MON))+'}'
 return 'module '+name+'('+', '.join(fields)+');\n'+body+'\nassign monitors='+monitor+';\nendmodule\n',co
allsv=''.join(defs);cases=[]
for rec in REC:
 canonical=(D/'canonical'/(rec['module']+'.sv')).read_text()
 for actual in rec['actual_native_masters']:
  idx=len(cases);g,n=instrument((C.P/'rtl'/(actual+'.sv')).read_text(),f'gold{idx}');a,_=instrument(canonical,f'gate{idx}');allsv+=g+a;cases.append((idx,n,actual))
# The control swaps two delivered output bits in one actual candidate, leaving other obligations intact.
m,_=instrument((D/'canonical'/(REC[0]['module']+'.sv')).read_text(),'mutant0',True);allsv+=m
shared=', '.join(['.clk(clk)','.rst_n(rst_n)','.c_i(c_i)']+[f'.sym_{rr}_{p}(sym_{rr}_{p})' for rr,p,w in SYMS])
for mutant in [False,True]:
 fields=['input wire clk','input wire rst_n','input wire [759:0] c_i']+[f'input wire [{w-1}:0] sym_{rr}_{p}' for rr,p,w in SYMS]+['output wire ok']
 lines=['module '+('top_mutant' if mutant else 'top_positive')+'('+', '.join(fields)+');']
 for idx,n,actual in cases:
  lines += [f'wire [{n-1}:0] go{idx},ao{idx}; wire [{SMW-1}:0] gm{idx},am{idx};',f'gold{idx} g{idx}({shared},.c_o(go{idx}),.monitors(gm{idx}));',f'{"mutant0" if mutant and idx==0 else "gate"+str(idx)} a{idx}({shared},.c_o(ao{idx}),.monitors(am{idx}));']
 lines+=['assign ok='+' && '.join(f'((go{i}==ao{i}) && (gm{i}==am{i}))' for i,_,_ in cases)+';','endmodule'];allsv+='\n'.join(lines)+'\n'
(O/'miter.sv').write_text(allsv);(O/'scope.json').write_text(json.dumps(dict(actual_native_modules=[a for _,_,a in cases],canonical_masters=[r['module'] for r in REC],leaf_input_obligation_bits_per_case=SMW,leaf_output_symbol_bits=sum(w for _,_,w in SYMS),real_output_bits_checked=sum(n for _,n,_ in cases),clock_reset_inputs_checked=True,registers_cycles_added=0,mutation='swap two delivered output bits in canonical lane0 candidate'),indent=1)+'\n');print('WIRING_MITER',len(cases),SMW,'input obligations/case',len(allsv),'bytes')
