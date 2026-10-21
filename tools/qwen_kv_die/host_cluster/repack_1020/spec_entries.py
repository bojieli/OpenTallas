import json,re,sys
sys.path.insert(0,'/home/ubuntu/scratch/kv-hroot10/tools')
import hr_parent as HP
F='rtl/qwen_sys/host_cluster_hroot10_1020/qkd_hr_cluster_e.v'
t=open(F).read(); e=t[t.index('module qkd_hr_cluster_e('):t.index('module qkd_hr_cluster_e_tied')]
ent={}
for m in re.finditer(r'^\s*(\w+)\s*(?:#\(.*?\))?\s+(\w+)\s*\((.*?)\);', e, re.M|re.S):
    for pm in re.finditer(r'\.(\w+)\((ck_\w+__\w+|ck_phy\[\d\])\)', m.group(3)):
        ent[pm.group(2)]=(m.group(2), pm.group(1))
fam={'ck_core':'core','ck_host':'host','ck_ingest':'ingest','ck_phy_fam':'phy','ck_phy':'phy'}
for k in sys.argv[1:]:
    sp=f'tools/ref_tile/specs_qhost_cluster/qkd_hr_cluster_{k}.json'; s=json.load(open(sp))
    s['top']='qkd_hr_cluster_e'; s['sources']=[F]
    pos={c['inst']:c for c in s['children']}
    W,H=s['outline']['w'],s['outline']['h']
    old=('ck_core','ck_host','ck_ingest','ck_phy_fam','ck_phy')
    for f in s['pins']:
        s['pins'][f]=[x for x in s['pins'][f] if x not in old and '__' not in x]
    for x in list(s['pin_ranges']):
        if x in old or '__' in x: s['pin_ranges'].pop(x)
    cps=[]
    for port,(inst,pin) in sorted(ent.items()):
        c=pos[inst]; v=c['view']; cell=v.rstrip('/').split('/')[-1]
        Wc,Hc,pins=HP.lef_pins(open(f'{v}/{cell}.lef').read())
        lx,ly=pins[pin]; lx,ly=HP.orient_xy(lx,ly,Wc,Hc,c['orient'])
        gx,gy=c['at'][0]+lx,c['at'][1]+ly
        f=HP.face_of(gx,gy,W,H); along=gy if f in 'EW' else gx
        if port.startswith('ck_phy['):
            if 'ck_phy' not in s['pins'].setdefault(f,[]): s['pins'][f].append('ck_phy')
            r=s['pin_ranges'].get('ck_phy',[1e9,-1e9]); s['pin_ranges']['ck_phy']=[round(min(r[0],along-3),2),round(max(r[1],along+3),2)]
        else:
            s['pins'].setdefault(f,[]).append(port); s['pin_ranges'][port]=[round(along-3,2),round(along+3,2)]
        cps.append(port)
    s['clock_ports']=sorted([q for q in cps if not q.startswith('ck_phy[')], key=lambda q:(q!='ck_core__core_peer',q))+[f'ck_phy[{i}]' for i in range(8)]
    s['clock_port']=s['clock_ports'][0]
    D=s['clock_entry_domains']
    for d in D.values(): d['ports']=[]
    for q in s['clock_ports']: D[fam[q.split('__')[0].split('[')[0]]]['ports'].append(q)
    s['clock_note']=('entries cluster (ref_tile contract): one parent clock entry port per hard-child clock pin (RTL qkd_hr_cluster_e = exact '
      'text transform of qkd_hr_cluster; tying each family\'s entries gives the original, wrapper qkd_hr_cluster_e_tied); the die/region '
      'clock delivers every entry; no parent clock cells. Families asynchronous: see clock_domain_note.')
    json.dump(s,open(sp,'w'),indent=1)
    print(k, s['clock_port'], len(s['clock_ports']), {f:len(v) for f,v in s['pins'].items()})
