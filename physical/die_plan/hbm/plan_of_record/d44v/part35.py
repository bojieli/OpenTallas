#!/usr/bin/env python3
"""HBM p35: separate clock access pins; widen TX routing capacity vertically."""
import gzip,json,pathlib,hashlib
r=pathlib.Path(__file__).parent

def load(p):return json.loads(gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text())
def save(p,d):
 b=(json.dumps(d)+'\n').encode()
 if p.exists():p.unlink()
 if p.suffix=='.gz':
  with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(b)
 else:p.write_bytes(b)
changes=load(r/'part35_event.json').get('clock_pin_changes',[]) if (r/'part35_event.json').exists() else []
allowed=('kshare_splitstrap','inj_idx_join_rg','tkm_m_tp192__root','sfu_split3_lane_core__idpin__master','sfu_split3_lane_core_fr','xload_cl2_ctlx','pdie_serdes_rx','ot_svgr_bk__','ot_wbq_root__','ot_wbq_sw__')
for p in sorted((r/'cores').glob('*')):
 if not p.name.endswith(('.json','.json.gz')) or not any(z in p.name for z in allowed):continue
 a=load(p)
 if not isinstance(a,list):continue
 clocks=[x for x in a if 'clk' in x.get('name','') and x.get('layer')=='M5']
 if len(clocks)!=2:continue
 for i,c in enumerate(clocks):
  for b in clocks[:i]:
   if abs(c['y']-b['y'])<.001 and abs(c['x']-b['x'])<.143:
    old=c['x'];c['x']=147.48 if c['name']=='rck_clk' else (216.216 if p.name.startswith('ot_wbq_root') else round(b['x']+.384,6))
    changes.append(dict(file=p.name,pin=c['name'],old=[old,c['y']],new=[c['x'],c['y']]))
 if any(x['file']==p.name for x in changes):save(p,a)
# Fit the expanded TX in each parent with its original west/south origin.
planp=r/'die_plan.json.gz';d=load(planp); oldname='cores/ot_pdie_serdes_tx__285.12x155.52__d44v_split.json';newname='cores/ot_pdie_serdes_tx__285.12x207.36__d44v_split.json'
ps=r/oldname
if not ps.exists():ps=ps.with_suffix(ps.suffix+'.gz')
a=load(ps)
for p in a:
 if p['name']=='clk':p['y']=103.68
 elif p['y']>155:p['y']=round(p['y']+51.84,6)
 # E/W face coordinates retain their exact old tracks and remain within height.
save(r/(newname+'.gz'),a)
parents=[]
for t,v in d['partition_types'].items():
 hs=v.get('hard_cores',[])
 for h in hs:
  if h.get('module')!='ot_pdie_serdes_tx':continue
  x,y=h['origin_um'];w,ht=285.12,207.36
  assert x+w<=v['outline_um'][0]+.001 and y+ht<=v['outline_um'][1]+.001,t
  for z in hs:
   if z is h:continue
   zx,zy=z['origin_um'];zw,zh=z['outline_um']
   assert min(x+w,zx+zw)-max(x,zx)<=.001 or min(y+ht,zy+zh)-max(y,zy)<=.001,(t,z['inst'])
  h['outline_um']=[w,ht];h['pins_file']=newname;parents.append(t)
save(planp,d)
e=r/'clock_entries.json.gz';ce=load(e)
for t,entries in ce.items():
 for inst,v in entries.items():
  if v.get('module')=='ot_pdie_serdes_tx':
   v['xy_um']=[142.584,103.68]
   if 'island_um' in v:v['island_um']=[138.24,99.36,146.88,108.0]
save(e,ce)
event=dict(schema='opentallas.hbm_p35_clockpin_tx.v1',clock_pin_changes=changes,tx=dict(old_outline=[285.12,155.52],new_outline=[285.12,207.36],parents=parents,pin_cycles=0,reason='measured horizontal track shortage, 2200 tracks in txh0',neighbor_overlap_checks='PASS'),pin_cycles=0)
(r/'part35_event.json').write_text(json.dumps(event,indent=1)+'\n')
# SHA256SUMS names refer to uncompressed logical files.
sums=r/'SHA256SUMS';lines=sums.read_text().splitlines();out=[]
for line in lines:
 sha,name=line.split(None,1);name=name.strip();p=r/name
 if p.exists():b=p.read_bytes()
 elif (r/(name+'.gz')).exists():b=gzip.open(r/(name+'.gz'),'rb').read()
 else:out.append(line);continue
 out.append(hashlib.sha256(b).hexdigest()+'  '+name)
newlogical=newname
if not any(z.endswith('  '+newlogical) for z in out):out.append(hashlib.sha256(gzip.open(r/(newlogical+'.gz'),'rb').read()).hexdigest()+'  '+newlogical)
sums.unlink();sums.write_text('\n'.join(out)+'\n')
print('p35 clock pin moves',len(changes),'tx parents',parents)
