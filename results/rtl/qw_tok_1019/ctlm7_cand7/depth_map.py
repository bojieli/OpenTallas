import json,re,sys
R='/srv/opentallas-scratch/claude/qw-ctlm7-1020'
d=json.load(open(R+'/generic7/parent.json'));m=d['modules']['qfd_tt_ctlm_dv_lpf_lp']
names={}
for n,v in m['netnames'].items():
    for k,b in enumerate(v['bits']):
        if isinstance(b,int): names.setdefault(b,[]).append((n,k))
srcs={}
for n,c in m['cells'].items():
    for p,bits in c['connections'].items():
        if c['port_directions'].get(p)=='output':
            for b in bits:
                if isinstance(b,int): srcs[b]=c['attributes'].get('src','')
t=json.load(open(R+'/native7/trace.json'))['metrics']['depth_trace']
src=open(R+'/generic7c/qfd_tt_ctlm_dv_np_lp.sv').read()
inst={}
for line in src.splitlines():
    mm=re.search(r' (u_\d+)\((.*)\);',line)
    if mm: inst[mm.group(1)]=mm.group(2)
seen=set();last=None
for r in t:
    u=r['cell'].split('.')[0]
    if u in seen: continue
    seen.add(u)
    y=re.search(r'\.(Y|Q)\(n_(\d+)\)',inst.get(u,''))
    if not y: continue
    b=int(y.group(2))
    nm=[x for x in names.get(b,[]) if not x[0].startswith('$')][:1]
    s=srcs.get(b,'').split('|')[0]
    key=(nm[0][0] if nm else '', s)
    acc=sum(x["weight"] for x in t[:t.index(r)+1])
    if key!=last: print(u, round(acc*float(open(R+"/native7/textbook.json").read() and json.load(open(R+"/native7/textbook.json"))["metrics"]["depth_ps"])/sum(x["weight"] for x in t)), nm, s[:90]); last=key
