#!/usr/bin/env python3
"""Audit immutable inherited native-SM LEFs and generate a physical seam reach ledger."""
import collections, itertools, json, math, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'results/arch/hbm_native_1013/sm'
manifest=json.loads((OUT/'component.json').read_text()); children={c['instance']:c for c in manifest['children']}; audits={}; pins={}
for c in children.values():
    lef=c['view_lef']
    if not lef or lef in audits: continue
    cp=subprocess.run(['python3','tools/hier_contract/child_lint.py',lef,'--libs',str(Path(lef).parent),'--cap',c['pg_top'] or 'M7','--json'],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try: result=json.loads(cp.stdout)
    except ValueError: result={'stdout':cp.stdout,'stderr':cp.stderr}
    audits[lef]={'rc':cp.returncode,'report':result}
    text=(ROOT/lef).read_text(); table={}
    for m in re.finditer(r'\bPIN\s+(\S+)\s+(.*?)(?=\n\s*END\s+\S+)',text,re.S):
        rect=re.search(r'RECT\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',m[2])
        if rect: v=list(map(float,rect.groups())); table[m[1]]=[(v[0]+v[2])/2,(v[1]+v[3])/2]
    pins[lef]=table
pairs=collections.defaultdict(lambda:{'bits':0,'max_manhattan_um':0,'missing_pin_bits':0})
for net in manifest['connections']:
    eps=[e for e in net['endpoints'] if e['instance']!='$boundary']
    if net['kind'] in ['clock','reset']: continue
    for aa,bb in itertools.combinations(eps,2):
        ca,cb=children[aa['instance']],children[bb['instance']]
        if ca['instance']==cb['instance']: continue
        key=tuple(sorted([ca['instance'],cb['instance']])); row=pairs[key]; row['bits']+=aa['width']
        for k in range(aa['width']):
            coords=[]
            for e,c in [(aa,ca),(bb,cb)]:
                width=c['boundary_ports'][e['port']]['width']; name=e['port']+('['+str(e['lsb']+k)+']' if width>1 else '')
                p=pins.get(c['view_lef'],{}).get(name)
                if p is None: coords=[]; break
                px=c['w_um']-p[0] if c['orientation']=='MY' else p[0]
                coords.append([px+c['xy_um'][0],p[1]+c['xy_um'][1]])
            if len(coords)==2:
                d=abs(coords[0][0]-coords[1][0])+abs(coords[0][1]-coords[1][1]); row['max_manhattan_um']=max(row['max_manhattan_um'],d)
            else: row['missing_pin_bits']+=1
rows=[{'endpoints':list(key),**row,'minimum_500um_segments':math.ceil(row['max_manhattan_um']/500),'closed':False,'owner':'/root/hbm_die_compiler'} for key,row in sorted(pairs.items())]
(OUT/'view_audit.json').write_text(json.dumps(audits,indent=2)+'\n'); (OUT/'seam_reach.json').write_text(json.dumps({'method':'Actual inherited LEF first RECT center, R0/MY placement; absent tile R5 export means tile seam lengths not measurable. Exact per-bit connectivity comes from component.json. Center packing is a candidate, not timing evidence.','rows':rows,'unmeasured_tile_seams':True,'all_rows_closed':False},indent=2)+'\n')
print(json.dumps({'view_audits':{k:v['rc'] for k,v in audits.items()},'seam_pairs':len(rows),'max_measurable_manhattan_um':max(r['max_manhattan_um'] for r in rows)}))
