import re,json,collections
p='/srv/opentallas-scratch/claude/hd4g/gen2c/case_a/'
bufs={};drivers={};fanout=collections.Counter();other=[]
for l in open(p+'die.v'):
 if ' dkh_' in l and l.lstrip().startswith(('BUF','INV')):
  a=re.search(r'(\w+) (dkh_\w+) \(\.A\((\w+)\), \.Y\((\w+)\)\)',l)
  if a:
   cell,n,i,o=a.groups();bufs[n]={'cell':cell,'A':i,'Y':o};drivers[o]=n;fanout[i]+=1
 if 'hfd_ckgen hb_ckgen' in l:other.append(l.strip())
n='dkh_P2';chain=[];seen=set()
while n in bufs and n not in seen:
 seen.add(n);chain.append(dict(name=n,**bufs[n],clock_buffer_loads=fanout[bufs[n]['Y']]));i=bufs[n]['A'];n=drivers.get(i,i)
print(json.dumps(dict(buffers=len(bufs),trace_from='dkh_P2/Y',ancestors=chain,terminal_net=n,ckgen=other),indent=2))
