import json,sys,os,re,collections,subprocess,hashlib
sys.path.insert(0,'/home/ubuntu/wt/type-reduce2-hbm-1025/tools/autopilot')
import ownership as O
WT='/home/ubuntu/wt/type-reduce2-hbm-1025'; R='/home/ubuntu/OpenTallas'; BASE='190ebb428'
PREL='physical/die_plan/hbm_arch/B2n'
def show(p): return subprocess.check_output(['git','-C',R,'show',f'{BASE}:{p}'])
can=json.loads(show('physical/die_plan/hbm/cores/harden/canonical_ports_split.json'))
masters=O.canonical_masters(can)
def entries(plan,reader):
    out={}
    for tn,t in plan['partition_types'].items():
        for h in t.get('hard_cores',[]):
            ps=O.pin_sig(reader(h['pins_file']))
            outl='x'.join(f'{float(x):g}' for x in h['outline_um'])
            out[(tn,h['inst'])]=('core:'+'|'.join((masters.get(h['module'],h['module']),outl,ps[1])),h)
    return out
pb=json.loads(show(PREL+'/die_plan.json')); pa=json.load(open(f'{WT}/{PREL}/die_plan.json'))
eb=entries(pb,lambda f: show(f'{PREL}/{f}').decode()); ea=entries(pa,lambda f: open(f'{WT}/{PREL}/{f}').read())
IB=json.load(open('/home/ubuntu/scratch/type-reduce2/items_before.json')); IA=json.load(open('/home/ubuntu/scratch/type-reduce2/items_after.json'))
dname_a={i['design']:i['item'] for i in IA}; dname_b={i['design']:i for i in IB}
# before design -> after items
b2a=collections.defaultdict(set); a2b=collections.defaultdict(set)
for k,(db,h) in eb.items():
    da=ea[k][0]; b2a[db].add(dname_a[da]); a2b[da].add(db)
own=[l.rstrip('\n').split('\t') for l in open('/tmp/trd_owners.tsv') if l.startswith('hbm\t')]
FACE=json.load(open('/home/ubuntu/scratch/type-reduce2/face_defer.json'))
canon_ids={}
for cn,c in can['types'].items():
    for tid,v in c['type_ids'].items(): canon_ids[re.sub(r'__[\d.]+x[\d.]+$','',tid)]=(cn,v)
mo=collections.defaultdict(set)   # master -> outlines
for i in IB:
    if i['kind']=='core': m,o,s=i['design'][5:].split('|'); mo[m].add(o)
ndes=collections.Counter(i['design'][5:].rsplit('|',1)[0] for i in IB if i['kind']=='core')
# types
T=pb['partition_types']; ninst=collections.Counter(p['type'] for p in pb['partitions'])
def tsig(t): return tuple(sorted(masters.get(h['module'],h['module']).split('#')[0] for h in t.get('hard_cores',[])))
rows=[]; byitem={i['item']:i for i in IB}
for r in own:
    item,kind,rep=r[1],r[2],r[10]
    it=byitem.get(item)
    if it is None: rows.append(('hbm',item,kind,rep,'?','?','not in plan_items')); continue
    if kind=='type':
        t=T[it['members'][0]]; sig=tsig(t); sib=[k for k,v in T.items() if k!=it['members'][0] and tsig(v)==sig and sig]
        reason='different-logic'; note='no other type binds the same hard-core masters'
        if sib:
            s=T[sib[0]]
            if [round(x,3) for x in s['outline_um']]!=[round(x,3) for x in t['outline_um']]: reason='outline'; note=f'same core masters as {sib[0]}, outline differs'
            else:
                bb=lambda x: sorted(json.dumps({k:v for k,v in b.items() if k in ('name','width','dir')},sort_keys=True) for b in x.get('buses',[]))
                fs=lambda x: sorted(json.dumps({k:v for k,v in f.items() if k in ('name','width','lane','bits')},sort_keys=True) for f in x.get('ft_slots',[]))
                if bb(s)==bb(t) and fs(s)!=fs(t): reason='ft-population'; note=f'same masters/outline/buses as {sib[0]}; ft slots differ'
                elif bb(s)!=bb(t) and fs(s)==fs(t): reason='glue-by-position'; note=f'same masters/outline as {sib[0]}; bus set/position glue differs'
                else: reason='glue-by-position' if bb(s)!=bb(t) else 'pin-positions'; note=f'same masters/outline as {sib[0]}; buses{"+ft" if fs(s)!=fs(t) else ""} differ'
        if it['members'][0]=='root': note+='; PATH-HBM root partition'
        rows.append(('hbm',item,kind,rep,reason,item,note)); continue
    d=it['design']; m,o,s=d[5:].split('|')
    after=sorted(b2a[d]); merged=[x for x in after]; 
    collapsed=any(len(a2b[da])>1 for k,(db,h) in eb.items() if db==d for da in [ea[k][0]])
    mods=it['members']; cid=[canon_ids.get(x) for x in mods]
    ids=set(); nonid=set()
    for c in cid:
        if c: 
            for sk in (c[1].get('straps') or {}): (ids if sk in ('map_lane_j','lane_lane_id','lane0_lane_id','lane1_lane_id','lane2_lane_id','lane3_lane_id') else nonid).add(sk)
    ac=after[0] if len(after)==1 else ';'.join(after)
    if 'tkm_tile' in m:
        reason='ID-constant'; ac='tkm_tile common_noid (x31) / terminal_noid (tile31) [PATH-HBM]'; note='tile_tid baked per tile + per-slot pins; DEFERRED to PATH-HBM no-ID templates (not in this delta)'
    elif any(x in m for x in ('hc_tail_rest','hc_sk_step0','hc_sk_steady')):
        reason='pin-positions'; ac=f'{m.split("#")[-1]} one table (deferred)'; note='root partition (PATH-HBM type) excluded from this delta; 2 per-slot tables -> 1'
    elif ids:
        reason='ID-constant'; note=f'ID {sorted(ids)} -> strap_* pins (option B)'+('' if collapsed else '; stays: own face class / table')
        if not collapsed and len(after)==1 and after[0]==item: pass
    elif nonid and ndes[f'{m}|{o}']>1:
        reason='edge'; note=f'non-ID constants {sorted(nonid)} (chain-first flags) stay baked'+('; merged same-flag replicas by one table' if collapsed else '')
    elif ndes[f'{m}|{o}']>1:
        reason='pin-positions'
        fd=FACE.get(m.split('#')[0]) or FACE.get(m.split('#')[-1])
        note=('one table per (master,outline) applied' if collapsed else 'per-slot table kept: '+(fd or 'faces/neighbour directions differ (one table turns ports away, G0C core_faces) -> needs parent re-place'))
    elif len(mo[m])>1:
        reason='outline'; note=f'{m} also at {sorted(mo[m]-{o})}'
    else:
        reason='different-logic'; note='only design of its RTL master'
    if not collapsed and reason in ('ID-constant',) and 'tkm' not in m and len(after)==1: ac=after[0]
    rows.append(('hbm',item,kind,rep,reason,ac,note))
with open('/home/ubuntu/scratch/type-reduce2/hbm_census.tsv','w') as f:
    f.write('die\titem\tkind\treplicas\treason\tafter_class\tnote\n')
    for r in rows: f.write('\t'.join(map(str,r))+'\n')
print(len(rows)); print(collections.Counter((r[2],r[4]) for r in rows))
na=len({r[5] for r in rows if r[2]=='core'}); print('after distinct core classes',na)
