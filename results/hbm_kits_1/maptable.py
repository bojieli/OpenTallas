import json,re,sys,collections
d=json.load(open(sys.argv[1])); rows=[l.rstrip('\n').split('\t') for l in open(sys.argv[2])]
m2g={}
for i,g in enumerate(d['groups']):
    for m in g['members']: m2g[m]=i
U5A_CHANGED={6,7,43,22,30,25,33,35,36,37,46,48,50,51,52,64,65}
R5={22,8,45,0,37,33,34,61,52,35}
QUAD5={44,58,59,0}
OTHER={13:'GEOM-REQ owner',15:'GEOM-REQ owner',70:'GEOM-REQ owner (r0c0_k1h0)',18:'GEOM-REQ owner',75:'GEOM-REQ owner',53:'GEOM-REQ owner',54:'PATH-HBM KIT-PLACED',27:'MASTER-PLAN FIX (lanes0_3 member)'}
def status(i):
    if i in R5: return 'SKIP R5'
    if i in U5A_CHANGED: return 'SKIP QUAD-5 U5a re-pin'
    if i in QUAD5: return 'SKIP QUAD-5 pending (div-7/ep)'
    if i in OTHER: return 'SKIP '+OTHER[i]
    return 'CANDIDATE'
out=collections.OrderedDict()
for r in rows:
    it,kind=r[0],r[1]
    if kind=='type': out[it]=('-','partition type (not a hard core; plan owner)'); continue
    base=re.sub(r'_[0-9a-f]{12}$','',it)
    gi=m2g.get(it, m2g.get(base))
    if gi is None and re.match(r'ot_hgi_coll_tkm_m_tp192__tile\d+$',it): gi=55 if it!='ot_hgi_coll_tkm_m_tp192__tile31' else 56
    if gi is None and re.match(r'ot_hgi_sfu_core_split3__lane\d+$',it): gi=62
    if gi is None:
        if 'bankq' in it or 'qhub' in it or 'vms_bank_native' in it or it.endswith('q2_hard_v8g__body'): out[it]=('-','RETIRED (absent from planU4f; superseded by bank128_pair / hnx_vms_bank_q0_faces / q2n2_body)'); continue
        out[it]=('-','UNMAPPED'); continue
    out[it]=(f"{gi}:{d['groups'][gi]['family'][:40]}", status(gi))
c=collections.Counter(v[1].split(' (')[0] for v in out.values())
print(json.dumps(c,indent=0))
json.dump(out,open(sys.argv[3],'w'),indent=0)
