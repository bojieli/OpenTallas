import json,collections,re
d=json.load(open(__import__('pathlib').Path(__file__).resolve().parents[1]/'hier_contract_1011'/'r25gq.json'))
A=collections.Counter(); N=collections.Counter()
for s in d['slots']:
  if s['kind']=='element':
    o=s['outline']; a=o['w']*o['h']/1e6
    c=s['cell']; k=re.sub(r'_(SE|SW|NE|NW|s\d|ne|nw|se|sw|hi|lo)\b.*','',c); k=re.sub(r'hfd_svc.*','hfd_svc',k); k=re.sub(r'hfd_attn_half.*','hfd_attn_half',k)
    A[k]+=a; N[k]+=1
tot=sum(A.values()); print('placed elements mm2',round(tot,1),'die',round(32984.288*25980.528/1e6,2))
for k,v in A.most_common(): print(k,N[k],round(v,2))
