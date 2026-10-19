import json,math
from pathlib import Path
rings=[]
for name,w,d,count in [('mul.key',32,5,4),('mul.hold',128,6,2)]+[(f'chunk.t{t}',32,4*t,3) for t in range(1,8)]+[('add.hold',32,5,8),('add.copy',2,11,1)]:
 n=d-2;k=max(1,(n-1).bit_length());checked=0
 for initial in range(1<<k):
  mem={};ptr=initial;din='cold';dout='cold'
  for edge in range(1,3*d+1):
   old=mem.get(ptr,'cold') if ptr<n else 'invalid'
   if ptr<n:mem[ptr]=din
   dout=old;din=edge;ptr=0 if ptr>=n-1 else ptr+1
   if edge>=d:
    assert dout==edge-d+1,(name,initial,edge,dout)
    checked+=1
 rings.append(dict(name=name,count=count,width=w,delay=d,rows=n,pointer_bits=k,all_initial_codes=1<<k,checks=checked,memory_bits_per_ring=w*n))
r=dict(verdict='PASS abstract OLD-row recurrence only; not production RTL reset/valid proof',rings=rings,ring_count=sum(x['count'] for x in rings),memory_bits=sum(x['count']*x['memory_bits_per_ring'] for x in rings),pin_data_ff=sum(x['count']*2*x['width'] for x in rings),pointer_ff=sum(x['count']*x['pointer_bits'] for x in rings),max_coherent_store_bits=max(x['memory_bits_per_ring'] for x in rings),explanation='Every invalid code saturates to zero on its first edge. That edge writes no real row and reads unknown, but din captures d1. The first real write at edge2 stores d1 in row0; its OLD read at edge N+2 equals the required D=N+2 delayed d1. All legal codes rotate similarly. Unknown memory/output before D is intentionally unqualified; reset does not alter the data or pointer. Actual validity/first-use must suppress those outputs.')
Path(__file__).with_name('ring_model.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='rings'}))
