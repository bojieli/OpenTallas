#!/usr/bin/env python3
"""FABLE-DIE-HEAD sideband reach audit: every one-cycle flop-to-flop status/start/raw-reset hop of the landing sideband
(ready/fault collect chain, FSTART writer/reader start relays, raw reset copies) in the published HEAD wrappers,
pin-to-pin Manhattan length from the plan (landing_contract pins, stage xy rows, anchors, relay comments).
usage: sb_audit.py PLAN PUBLISHED_DIR [--limit 350] [--tsv OUT]"""
import json,re,sys,os,collections
P=json.load(open(sys.argv[1])); PUB=sys.argv[2]
LIM=float(sys.argv[sys.argv.index('--limit')+1]) if '--limit' in sys.argv else 350.0
TSV=sys.argv[sys.argv.index('--tsv')+1] if '--tsv' in sys.argv else None
rows=[]; summ={}
for tn,t in sorted(P['partition_types'].items()):
    f=os.path.join(PUB,t['module']+'.sv')
    if not os.path.exists(f): summ[tn]='NO WRAPPER'; continue
    src=open(f).read(); c=t['clock']; W,H=t['outline_um']
    pin={p['name']:p['xy_um'] for p in c.get('landing_contract',{}).get('pins',[])}
    pos={}; est=set()
    org=c.get('landing_reader_start',{}).get('origin_rect_um')
    origin=[(org[0]+org[2])/2,(org[1]+org[3])/2] if org else (c.get('start_capture_um') or c.get('tap_um') or [W/2,H/2])
    anc=c.get('landing_status_anchors',{}) or {}
    sin=c.get('landing_status_input_stages',{}) or {}
    idn=lambda s: re.sub(r'\W','_',s)
    for tgt,rings in sin.items():
        for r,st in rings.items():
            for k,s in enumerate(st): pos[f'u_cland_sin_{idn(tgt)}_{idn(r)}_{k}']=s['xy_um']
    pos.update(anc)
    for key,pre in (('landing_writer_start','u_cland_writer_start_'),('landing_reader_start','u_cland_reader_start_')):
        for b,br in (c.get(key,{}) or {}).get('branches',{}).items():
            for k,s in enumerate(br['stages']): pos[f'{pre}{b}_{k}']=s['xy_um']
    for lr in c.get('landing_local_resets',[]) or []: pos['u_cland_lrst_'+lr['name']]=lr['xy_um']
    # raw relays with "@ (x, y)" comments
    for m in re.finditer(r'ot_dp_rrelay\s+(\w+)\s*\(([^;]*?)\);[^\n]*?@ \(([-\d.]+), ([-\d.]+)\)',src): pos[m.group(1)]=[float(m.group(3)),float(m.group(4))]
    drv={}; edges=[]  # net -> driver inst
    insts={}
    for m in re.finditer(r'ot_dp_landing_collect\s+#\(\.N\((\d+)\)\)\s+(\w+)\s*\((.*?)\);',src,re.S):
        name,body=m.group(2),m.group(3)
        ri=re.search(r'\.ready_i\(\{(.*?)\}\)',body,re.S).group(1); ro=re.search(r'\.ready_o\((\w+)\)',body).group(1)
        rst=re.search(r'\.rst_n\((\w+)\)',body).group(1)
        insts[name]=dict(kind='status',ins=[x.strip() for x in ri.split(',')],rst=rst); drv[ro]=name
    for m in re.finditer(r'ot_dp_landing_relay(?:_rep)?\s+(?:#\([^)]*\)\)\s+)?(\w+)\s*\((.*?)\);',src,re.S):
        name,body=m.group(1),m.group(2)
        d=re.search(r'\.d\((\w+)\)',body); q=re.search(r'\.q\((\w+)\)',body); rst=re.search(r'\.rst_raw_n\((\w+)\)',body)
        insts[name]=dict(kind='start',ins=[d.group(1)],rst=rst.group(1) if rst else None); drv[q.group(1)]=name
    for m in re.finditer(r'ot_dp_rrelay\s+(\w+)\s*\(([^;]*?)\);',src):
        name,body=m.group(1),m.group(2); d=re.search(r'\.d\((\w+)\)',body); q=re.search(r'\.q\((\w+)\)',body)
        if d and q: insts[name]=dict(kind='raw',ins=[d.group(1)],rst=None); drv[q.group(1)]=name
    for a,b in re.findall(r'assign\s+(\w+)\s*=\s*(\w+)\s*;',src): drv.setdefault(a,'='+b)
    def resolve(net,d=0):
        x=drv.get(net)
        while isinstance(x,str) and x.startswith('=') and d<20: net=x[1:]; x=drv.get(net); d+=1
        return x,net
    # fixed positions
    for n in insts:
        m=re.fullmatch(r'u_cland_up_(\w+)',n)
        if m and 'cland_up_fault_'+m.group(1) in pin: pos[n]=pin['cland_up_fault_'+m.group(1)]
        m=re.fullmatch(r'u_cland_fstart_(\w+)',n)
        if m and 'cland_fstart_out_'+m.group(1) in pin: pos[n]=pin['cland_fstart_out_'+m.group(1)]
        m=re.fullmatch(r'u_cland_rst_(\w+)',n)
        if m and 'cland_dn_fault_'+m.group(1) in pin: pos.setdefault(n,pin['cland_dn_fault_'+m.group(1)])
    def srcpos(net):
        m=re.fullmatch(r'(?:landing_ready|landing_fault|cland_ok|cland_bad)_(\w+)',net)
        if m:
            b=m.group(1)
            for k in ('cland_dn_fault_'+b,'fclk_in_'+b):
                if k in pin: return 'ring:'+b,pin[k]
        if net in('cland_start','cland_start_d'): return 'origin',origin
        return None,None
    E=[]
    for n,i in insts.items():
        for net in i['ins']:
            d,net2=resolve(net)
            if d in insts: E.append((d,n,i['kind']))
            else:
                s,xy=srcpos(net2)
                if s: pos[s]=xy; E.append((s,n,i['kind']))
        if i['rst'] and i['kind']!='raw':
            d,net2=resolve(i['rst'])
            if d in insts: E.append((d,n,'rawrst'))
    # reader start chains end at the ring
    for n in insts:
        m=re.fullmatch(r'u_cland_reader_start_(\w+?)_(\d+)',n)
        if m:
            b=m.group(1)
            if not any(re.fullmatch(rf'u_cland_reader_start_{re.escape(b)}_{int(m.group(2))+1}',x) for x in insts):
                for k in ('cland_dn_fault_'+b,'fclk_in_'+b):
                    if k in pin: pos['ring:'+b]=pin[k]; E.append((n,'ring:'+b,'start')); break
    nodes={a for e in E for a in e[:2]}
    unk=[n for n in nodes if n not in pos]
    adj=collections.defaultdict(list)
    for a,b,k in E:
        if k!='rawrst': adj[a].append(b); adj[b].append(a)
    cur={n:list(pos.get(n,[W/2,H/2])) for n in nodes}
    for it in range(300):
        for n in unk:
            nb=adj[n]
            if nb: cur[n]=[sum(cur[x][0] for x in nb)/len(nb),sum(cur[x][1] for x in nb)/len(nb)]
    worst=collections.defaultdict(float); nbad=0
    for a,b,k in E:
        L=abs(cur[a][0]-cur[b][0])+abs(cur[a][1]-cur[b][1]); e='est' if (a in unk or b in unk) else 'xy'
        worst[k]=max(worst[k],L)
        if L>LIM: nbad+=1; rows.append((tn,k,a,b,round(L,1),e))
    summ[tn]=dict(size=(W,H),edges=len(E),unplaced=len(unk),over=nbad,worst={k:round(v) for k,v in worst.items()},
                  rows=[k for k in ('landing_reader_start','landing_writer_start','landing_status_input_stages','landing_status_anchors','landing_local_resets') if k in c])
print('type size edges unplaced over_%d worst(status/start/raw/rawrst) rows'%LIM)
for tn,s in summ.items(): print(tn,s if isinstance(s,str) else '%dx%d e=%d unpl=%d OVER=%d %s rows=%d'%(s['size'][0],s['size'][1],s['edges'],s['unplaced'],s['over'],s['worst'],len(s['rows'])))
rows.sort(key=lambda r:(r[0],-r[4]))
print('\nOVER-LIMIT HOPS',len(rows))
for r in rows[:int(os.environ.get('SHOW','80'))]: print('\t'.join(map(str,r)))
if TSV: open(TSV,'w').write('type\tclass\tfrom\tto\tum\tpos\n'+''.join('\t'.join(map(str,r))+'\n' for r in rows))
