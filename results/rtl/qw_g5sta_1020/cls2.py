import re,sys,collections,json
tcl,summ,corner=sys.argv[1],sys.argv[2],sys.argv[3]
T=833.333
lat={}   # pin -> (clock, latency) last wins
mcp={}   # inst -> (setup,hold)
rel=re.compile(r'set_clock_latency -source -clock \[get_clocks (\S+)\] (\S+) \[get_pins \{(\S+)\}\]')
rem=re.compile(r'set_multicycle_path -(setup|hold) (\d+) .*-to \[get_pins \{([^}]*)\}\]')
for line in open(tcl):
    if line.startswith('set_clock_latency'):
        m=rel.match(line)
        if m: lat[m.group(3)]=(m.group(1),float(m.group(2)))
    elif line.startswith('set_multicycle_path'):
        m=rem.match(line)
        if m:
            for p in m.group(3).split():
                i=p.split('/')[0]
                d=mcp.setdefault(i,{}); d[m.group(1)]=int(m.group(2))
ilat=collections.defaultdict(list)
for p,(c,v) in lat.items(): ilat[p.split('/')[0]].append((c,v))
def L(i):
    v=ilat.get(i)
    if not v: return None,None
    vals=sorted(x[1] for x in v); return v[0][0], vals[len(vals)//2]
def fam(inst):
    inst=re.sub(r'\[\d+\]','',inst)
    inst=re.sub(r'_\d+(?=_|$)','_N',inst)
    return re.sub(r'(_N)+','_N',inst)
RST=re.compile(r'^(rstt_|rs_bump|rly_rst_)')
cls=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,None]))
tot=collections.Counter(); worst=collections.defaultdict(float)
for line in open(summ):
    p=line.split()
    if len(p)<5 or '(' not in line: continue
    try: s=float(p[-1])
    except: continue
    if s>=0: continue
    st,en=p[0],p[2]; si,ei=st.split('/')[0],en.split('/')[0]
    pin=en.split('/')[-1] if '/' in en else ''
    cs,ls=L(si); ce,le=L(ei)
    d=None if ls is None or le is None else ls-le
    if RST.match(si) or re.match(r'(rst|rs|en)(\[|_n|$)',pin) and RST.match(si):
        c='reset_tree'
    elif ei in mcp:
        c='landing_window'
    elif cs and ce and cs!=ce:
        c='cross_domain'
    elif d is not None and abs(d)>200:
        c='owed_unlanded_crossing'
    elif d is None:
        c='view_model_unmeasured'
    else:
        c='data_path_local'
    k=(fam(si),fam(ei))
    e=cls[c][k]; e[0]+=1
    if s<e[1]: e[1]=s; e[2]=(st,en,d,mcp.get(ei))
    tot[c]+=1; worst[c]=min(worst[c],s)
out={'corner':corner,'classes':{c:{'endpoints':tot[c],'worst':worst[c]} for c in tot}}
print(json.dumps(out))
for c in cls:
    print('##',c,tot[c],worst[c])
    for k,v in sorted(cls[c].items(),key=lambda kv:kv[1][1])[:25]:
        print(f'  {v[1]:9.1f} {v[0]:6d} {k[0]} -> {k[1]}  eg {v[2]}')
