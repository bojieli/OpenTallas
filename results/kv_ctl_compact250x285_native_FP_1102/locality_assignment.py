"""Permute equal-master internal FF sites to retain prior physical source-cone locality."""
import csv,gzip,json,collections
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parent/'kv_ctl_compact250x285_PREP_1102';poses=json.loads(gzip.decompress((O/'initial_FF_sites.json.gz').read_bytes()));old={q['name']:q for q in csv.DictReader(open('/srv/opentallas-scratch/claude/codex-kv-ctl-rowfix-r2-0250/collector/placed.csv'))}
selected={q['FF'] for q in json.load(open(P/'FF_envelope_PREP.json'))['centered_public']};por=json.load(open(O/'FF_site_report.json'))['reset_anchor_FF']
# Public pin FFs remain immutable; identify original centered nonpublic names from the allocator's anchors.
import runpy
# Incidence inventory produced by the envelope includes every public FF via old actual graph.
import sys
sys.path.insert(0,str(O.parents[1]/'tools/autopilot'));import geom_rules as G,re
D=G.Design('/srv/opentallas-scratch/claude/codex-kv-ctl-compact250-0430/collector/geom.tsv');ids={c[6]:i for i,c in D.cells.items()};public=set()
for p in D.pins:
 if p['name'] in ['rst_n','por_n'] or p['sig'] in ['POWER','GROUND','CLOCK'] or G.CLOCK_PIN_RE.search(p['name']) or re.search(G.STRAP_RE_DEFAULT,p['name']):continue
 n=D.pin_net.get(p['k']);todo=[n] if n is not None else [];seen=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  if p['io']=='OUTPUT':
   e=D.nets[n][1]
   if not e or e[0]!='i':continue
   if D.kind(e[1])=='S':public.add(D.cells[e[1]][6])
   elif D.kind(e[1])=='B':todo.extend(nn for nn,ck in D.cell_in.get(e[1],[]) if not ck)
  else:
   for e in D.nets[n][2]:
    if e[0]!='i' or e[2]:continue
    if D.kind(e[1])=='S':public.add(D.cells[e[1]][6])
    elif D.kind(e[1])=='B':todo.extend(D.drives.get(e[1],[]))
assert len(public)==6846

def morton(x,y,w,h):
 a=max(0,min(1023,int(x/w*1023)));b=max(0,min(1023,int(y/h*1023)));return sum(((a>>k)&1)<<(2*k)|((b>>k)&1)<<(2*k+1) for k in range(10))
groups=collections.defaultdict(list)
for p in poses:
 if p['name'] not in public|{por}:groups[p['master']].append(p)
(O/'internal_names.json').write_text(json.dumps([p['name'] for group in groups.values() for p in group]))
for group in groups.values():
 sites=sorted(group,key=lambda q:morton((q['ll_dbu'][0]+q['size_dbu'][0]/2)/1000,(q['ll_dbu'][1]+q['size_dbu'][1]/2)/1000,250.56,285.12));names=sorted(group,key=lambda q:morton(float(old[q['name']]['x'])+float(old[q['name']]['w'])/2,float(old[q['name']]['y'])+float(old[q['name']]['h'])/2,371.52,371.52));new=[(q['ll_dbu'][:],q['orient']) for q in sites]
 for p,(ll,ori) in zip(names,new):p['ll_dbu']=ll;p['orient']=ori
(O/'FF_sites.json.gz').write_bytes(gzip.compress(json.dumps(poses,separators=(',',':')).encode(),mtime=0));print('REASSIGNED_INTERNAL',sum(map(len,groups.values())))
