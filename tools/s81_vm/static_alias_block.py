"""Fail-closed evaluator for clockless, statically controlled blocking wiring blocks.
Only integer-controlled loops/conditions and bit aliases/constants are accepted.
Assignments are applied in source order before final aliases are emitted, preserving overrides.
"""
def evaluate(block,path,index,width,const):
 integer_ids={n['addr']for n in nodes(block)if n['type']=='VAR'and n.get('dtypeName')=='integer'};env={};state={}
 def number(n):
  t=n['type']
  if t=='CONST':return const(n)
  if t=='CRESET':return 0
  if t=='VARREF'and n['varp']in env:return env[n['varp']]
  if t=='SEL':return(number(n['fromp'][0])>>number(n['lsbp'][0]))&((1<<n['widthConst'])-1)
  if t=='COND':return number(n['thenp'][0]if number(n['condp'][0])else n['elsep'][0])
  if t in ('ADD','SUB','MULS','MUL','GTS','LTS','EQ','LT','GT','LTE','GTE'):
   a,b=number(n['lhsp'][0]),number(n['rhsp'][0]);return {'ADD':lambda:a+b,'SUB':lambda:a-b,'MULS':lambda:a*b,'MUL':lambda:a*b,'GTS':lambda:int(a>b),'LTS':lambda:int(a<b),'EQ':lambda:int(a==b),'LT':lambda:int(a<b),'GT':lambda:int(a>b),'LTE':lambda:int(a<=b),'GTE':lambda:int(a>=b)}[t]()
  raise ValueError('Non-static alias control/expression '+t+' '+n.get('loc',''))
 def value(n,destination=False):
  t=n['type']
  if t=='VARREF':
   if n['varp']in integer_ids:
    v=number(n);return[('CONST',str((v>>i)&1),0)for i in range(width(n))]
   bits=[(path,n['varp'],i)for i in range(width(n))];return bits if destination else[state.get(b,b)for b in bits]
  if t=='SEL':
   b=value(n['fromp'][0],destination);start=number(n['lsbp'][0]);return b[start:start+n['widthConst']]
  if t=='CONST':return[('CONST',str((const(n)>>i)&1),0)for i in range(width(n))]
  if t=='CONCAT':return value(n['rhsp'][0])+value(n['lhsp'][0])
  # Integer casts/part selects used for static tags are evaluated exactly.
  v=number(n);return[('CONST',str((v>>i)&1),0)for i in range(width(n))]
 class StopLoop(Exception):pass
 def run(n):
  t=n['type']
  if t in ('BEGIN','ALWAYS','INITIALSTATICSTMT'):
   for x in n.get('stmtsp',[]):run(x)
  elif t=='ASSIGN':
   l=n['lhsp'][0];rr=n['rhsp'][0]
   if l['type']=='VARREF'and l['varp']in integer_ids:env[l['varp']]=number(rr)
   else:
    dest,src=value(l,True),value(rr);assert len(dest)==len(src),(n.get('loc'),len(dest),len(src))
    for a,b in zip(dest,src):state[a]=b
  elif t=='LOOP':
   for iteration in range(256):
    try:
     for x in n['stmtsp']:run(x)
    except StopLoop:break
   else:raise ValueError('Unbounded static alias loop')
  elif t=='LOOPTEST':
   if not number(n['condp'][0]):raise StopLoop()
  elif t not in ('VAR',):raise ValueError('Unsupported alias statement '+t+' '+n.get('loc',''))
 run(block);return state

def nodes(n):
 if isinstance(n,dict):
  yield n
  for v in n.values():yield from nodes(v)
 elif isinstance(n,list):
  for v in n:yield from nodes(v)
