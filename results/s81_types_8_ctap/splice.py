import json,re,sys
# splice.py ORIG NEW OUT : minimal-diff plan text: ORIG text with only the changed partition_types values replaced by NEW's text
o_txt=open(sys.argv[1]).read(); n_txt=open(sys.argv[2]).read()
O=json.loads(o_txt); N=json.loads(n_txt)
for k in set(O)|set(N):
    if k!='partition_types': assert O.get(k)==N.get(k),k
ch=[t for t in N['partition_types'] if O['partition_types'].get(t)!=N['partition_types'][t]]
assert set(O['partition_types'])==set(N['partition_types'])
dec=json.JSONDecoder()
def span(txt,tn):
    pt=txt.index('"partition_types"')
    ms=[m for m in re.finditer(r'"%s"\s*:\s*'%re.escape(tn),txt) if m.start()>pt]
    for m in ms:
        try: v,e=dec.raw_decode(txt,m.end())
        except Exception: continue
        if isinstance(v,dict) and 'hard_cores' in v or isinstance(v,dict) and 'outline_um' in v: return m.end(),e
    raise KeyError(tn)
spans=sorted((span(o_txt,t),t) for t in ch)
out=[];last=0
for (a,b),t in spans:
    na,nb=span(n_txt,t); out+=[o_txt[last:a],n_txt[na:nb]]; last=b
out.append(o_txt[last:]); r=''.join(out)
assert json.loads(r)==N,'splice changed content'
open(sys.argv[3],'w').write(r); print('types spliced',len(ch))
