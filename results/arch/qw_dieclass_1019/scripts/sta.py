import sys,re,json,collections
C=sys.argv[1]; corner=sys.argv[2]
m={}
for l in open(C+'/dieclk/geom/blocks.tsv'):
    p=l.rstrip('\n').split('\t'); m[p[0]]=p[1]
nv=set(json.load(open(C+'/bind.json'))['no_view'])
def fam(inst):
    ms=m.get(inst)
    if ms is None: return 'top/std:'+re.sub(r'\d+','#',inst)[:30]
    if ms.startswith('qfd_rst_rep'):
        x=re.sub(r'_\d+$','',inst); x=re.sub(r'__fo\d+__r\d+','',x); return 'RST:'+x.replace('rstt_rst_','')
    sb='*' if ms in nv else ''
    if ms.startswith('qfd_landh0'): return 'LAND_H0'+sb
    if ms.startswith('qfd_landh'): return 'LAND'+sb
    if re.match(r'qfd_rly(h0|r0)',ms): return 'RLY_H0'+sb
    if ms.startswith('qfd_rly'): return 'RLY'+sb
    short={'qfd_c_b16_dv':'CB16','qfd_dv_slice2_e':'SLICE2E','qfd_dv_slice2_w':'SLICE2W','qfd_native59_dv_service':'N59','qfd_tt_ctlm_dv':'CTLM',
           'qfd_collective_static_io_production':'COLL_IO','qfd_sys_face_mu_dhobs':'MU_DHOBS','ot_qkvd_ucie_x64_phy':'UCIE_KV'}.get(ms,ms.replace('qfd_','').replace('ot_qfd_',''))
    return short+sb
cls=collections.defaultdict(lambda:[0,0,1e18,None])
fams=collections.defaultdict(lambda:[0,1e18])
rx=re.compile(r'^(\S+)\s+\(\S+\)\s+(\S+)\s+\(\S+\)\s+(-?[0-9.]+)\s*$')
nviol=0;n=0
for l in open(C+f'/sta_r22k_{corner}/grt_{corner}_summary.rpt'):
    r=rx.match(l)
    if not r: continue
    n+=1
    s,e,sl=r.group(1),r.group(2),float(r.group(3))
    fs=fam(s.split('/')[0]); fe=fam(e.split('/')[0])
    k=fs+' -> '+fe; c=cls[k]; c[1]+=1
    if sl<0:
        nviol+=1; c[0]+=1
        if sl<c[2]: c[2]=sl; c[3]=s+' -> '+e
print(f'## {corner} endpoints {n} violating {nviol}')
for k,v in sorted(cls.items(),key=lambda kv:kv[1][2]):
    if v[0]: print(f'{k}\t{v[0]}/{v[1]}\t{v[2]:.0f}\t{v[3]}')
