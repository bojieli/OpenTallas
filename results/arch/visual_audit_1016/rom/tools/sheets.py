import json,subprocess,os,sys
TILE=True
OUT=sys.argv[1]; os.makedirs(OUT,exist_ok=True)
def load(f):
    d=json.load(open(f)); return d['findings'] if isinstance(d,dict) else d
def imgs(x):
    r=[]
    for p in x.get('images',[]):
        if not p.startswith('/'): p='/tmp/visrom/'+p
        if p.endswith('.png') and os.path.exists(p): r.append(p)
    pref=lambda p:(0 if 'congestion' in p else 1 if 'density' in p else 2 if 'placement' in p else 3)
    return sorted(r,key=pref) if TILE else r
def sheet(name,title,findings,per=1,cap=12):
    global TILE; TILE=per==1
    items=[]
    for x in sorted(findings,key=lambda x:x['severity']):
        for p in imgs(x)[:per]:
            lab=f"{x['id']} sev{x['severity']} {x['master'][:40]} | {x['owner']} | {x['see'][:90]}"
            items.append(f"{p}::{lab}")
        if len(items)>=cap: break
    if not items: print('no images',name); return
    subprocess.run(['python3','/tmp/visrom/tools/montage.py',f'{OUT}/{name}',title]+items[:cap],check=True)
parts={'qcompute':'/tmp/visrom/qwen_compute/findings_qcompute.json','qkv':'/tmp/visrom/qwen_kvsys/findings_qkv.json',
       's81_hub':'/tmp/visrom/s81/findings_s81_hub.json','s81_fabric':'/tmp/visrom/s81/findings_s81_fabric.json'}
F={k:load(v) for k,v in parts.items() if os.path.exists(v)}
D=load('/tmp/visrom/die/findings_die.json')
if 'qcompute' in F: sheet('contact_qwen_compute_tiles.png','VIS-ROM 10-16: Qwen compute die - worst tiles',F['qcompute'])
if 'qkv' in F: sheet('contact_qwen_kv_tiles.png','VIS-ROM 10-16: Qwen KV/system die - worst tiles',F['qkv'])
s81=F.get('s81_hub',[])+F.get('s81_fabric',[])
if s81: sheet('contact_s81_tiles.png','VIS-ROM 10-16: DeepSeek S81 die - worst tiles',s81)
for die,nm,t in (('qwen_compute','contact_die_qwen_compute.png','Qwen compute die r2b2 / r2f2 plan'),('qwen_kvsys','contact_die_qwen_kv.png','Qwen KV die kvs11 / kvs10'),('s81','contact_die_s81.png','S81 die c21h + VM-centred v2 plan')):
    sheet(nm,'VIS-ROM 10-16 DIE: '+t,[x for x in D if x['die']==die],per=3)
