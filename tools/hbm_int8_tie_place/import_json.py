import json,sys
from pathlib import Path
j=json.load(open(sys.argv[1]));m=j['modules']['ot_smh_int8_tile_safe'];a=['module ot_smh_int8_tile_safe('+','.join(m['ports'])+');'];bits={}
for n,v in m['ports'].items():
 b=v['bits'];a.append(v['direction']+(' [%d:0]'%(len(b)-1) if len(b)>1 else '')+' '+n+';')
 for k,x in enumerate(b):bits[x]=n+('[%d]'%k if len(b)>1 else '')
allbits={x for c in m['cells'].values() for b in c['connections'].values() for x in b if isinstance(x,int)}
for x in sorted(allbits-set(bits)):bits[x]='n%d'%x;a.append('wire n%d;'%x)
def val(x):return bits[x] if isinstance(x,int) else "1'b"+x
for n,c in m['cells'].items():
 assert not c['parameters'],(n,c['parameters'])
 a.append(c['type']+' '+chr(92)+n+'  ('+','.join('.'+p+'('+('{' + ','.join(val(x) for x in reversed(b))+'}' if len(b)>1 else val(b[0]))+')' for p,b in c['connections'].items())+');')
a.append('endmodule');Path(sys.argv[2]).write_text('\n'.join(a)+'\n')
