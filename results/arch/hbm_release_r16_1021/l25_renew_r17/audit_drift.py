import json,re,subprocess,hashlib,collections,sys
W='/home/ubuntu/wt/claude-hbm-r17-1021'
r=json.load(open('/home/ubuntu/artifacts/hdie-d4/claude_hbm_r16q_full_1021/planqM/unread/S5/review_transfer.json'))
c=json.load(open('/home/ubuntu/artifacts/hdie-d4/claude_hbm_r16q_full_1021/planqM/net/post_landing.json'))
D={'rtl/hbm_accel/die_glue/scoped_d4g/pgslice.sv':'167cae17c','rtl/hbm_accel/generic/collective/p2p/ot_hfd_coll_q_hard_v5.sv':'fcf411d6c',
'rtl/hbm_accel/generic/collective/p2p/ot_hfd_coll_q_hard_v8g.sv':'fcf411d6c','rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv':'74d218d51',
'rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv':'74d218d51','rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static_am.sv':'198cbe31e',
'rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv':'911b90eb2'}
def git(*a): return subprocess.check_output(['git','-C',W]+list(a)).decode()
def headers(t):
    t=re.sub(r'//[^\n]*','',t); t=re.sub(r'/\*.*?\*/','',t,flags=re.S)
    out={}
    for m in re.finditer(r'\bmodule\s+(\w+)\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*\((.*?)\);',t,re.S):
        ports=[]
        for d in re.finditer(r'\b(input|output|inout)\b([^;]*?)(?=\b(?:input|output|inout)\b|$)',m.group(3),re.S):
            s=re.sub(r'\s+',' ',d.group(0)).strip().rstrip(',')
            ports.append(s)
        out[m.group(1)]=ports
    return out
ent_by_inst=collections.defaultdict(list); cons=collections.defaultdict(list)
for e in r['approved_entries']:
    ent_by_inst[e['instance']].append(e)
    for n in set(re.findall(r'"instance": "(\w+)"',json.dumps(e.get('evidence')))): cons[n].append(e['instance']+'.'+e['port'])
res={}
for p,old in D.items():
    cur=hashlib.sha256(open(f'{W}/{p}','rb').read()).hexdigest(); assert cur!=r['source_sha256'][p]
    assert hashlib.sha256(subprocess.check_output(['git','-C',W,'show',f'{old}:{p}'])).hexdigest()==r['source_sha256'][p]
    ho=headers(git('show',f'{old}:{p}')); hn=headers(open(f'{W}/{p}').read())
    insts=[n for n,v in c['instances'].items() if v['source']==p or p in (v.get('rtl_deps') or [])]
    masters=sorted({c['instances'][n]['master'] for n in insts})
    # master modules defined in this file: compare headers
    hdr={}
    for m in sorted(set(ho)|set(hn)):
        if ho.get(m)!=hn.get(m):
            a=set(ho.get(m) or []); b=set(hn.get(m) or [])
            hdr[m]={'removed':sorted(a-b),'added':sorted(b-a),'new_module':m not in ho}
    drv=[e['instance']+'.'+e['port'] for n in insts for e in ent_by_inst.get(n,[])]
    cn=sorted({x for n in insts for x in cons.get(n,[])})
    res[p]=dict(old_rev=old,old_sha256=r['source_sha256'][p],new_sha256=cur,instances=len(insts),masters=masters,
                port_header_changes=hdr,reviewed_driver_entries=drv,reviewed_entries_naming_as_consumer=cn)
json.dump(res,open('/home/ubuntu/scratch/hbmb-chain/l25/audit.json','w'),indent=1)
for p,v in res.items():
    print('==',p,v['old_rev'],'insts',v['instances'],v['masters'])
    print('   driver entries',v['reviewed_driver_entries'],' consumer-named',v['reviewed_entries_naming_as_consumer'])
    for m,h in v['port_header_changes'].items(): print('   HDR',m,json.dumps(h)[:600])
