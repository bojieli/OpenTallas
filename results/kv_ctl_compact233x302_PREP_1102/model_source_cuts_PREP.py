"""Current source nets in proposed geometry; native-phase PG prediction, no CAD verdict."""
from pathlib import Path
import os,subprocess
O=Path(__file__).resolve().parent
os.environ['FF_SITE_FILE']='FF_sites_PREP.json.gz'
os.environ['RELAX_ITERS']='100'
os.environ['DENSITY_WEIGHT']='0'
os.environ['COMB_DENSITY']='0'
os.environ['MACRO_LAYOUT']=''
s=subprocess.check_output(['git','show','a60a58293:results/kv_ctl_compact250x285_native_FP_1102/model_channels.py'],cwd=O.parents[1]).decode().split('rr=G.r2r_metrics(D);')[0]
s=s.replace('250.56','233.28').replace('285.12','302.4').replace('246.24','228.96').replace('280.8','298.08').replace('125.28','116.64').replace('142.56','151.2')
insert="""D.die=(0.,0.,233.28,302.4)
pp={q['name']:q for q in json.load(open(O/'candidate_parent_pins_PREP.json'))['pins']}
assert set(pp)=={p['name'] for p in D.pins if p['sig'] not in ['POWER','GROUND']}
for p in D.pins:
 if p['name'] in pp:p['x'],p['y']=pp[p['name']]['x'],pp[p['name']]['y']
news={q['name']:q for q in json.load(open(O/'candidate_macro_sites_PREP.json'))}
for i,c in list(D.cells.items()):
 if c[0]=='M':
  q=news[c[6]];x,y=q['x'],q['y'];D.cells[i]=tuple(list(c[:2])+[x,y,x+q['width'],y+q['height']]+list(c[6:]))
"""
s=s.replace('for p in poses:',insert+'for p in poses:',1)
exec(compile(s,str(O/'model_source_cuts_PREP.py'),'exec'))
import inspect,collections,re,csv,json,gzip,math
rr=G.r2r_metrics(D);pr=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT));nominal=G.demand_metrics(D)
# Reconstruct expected row-grid power phase from the actual macro-free native8.64um strip.
C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-compact250-0430/collector');tracks={q['layer']:q for q in json.load(open(C/'tracks.json'))['tracks']};pg=list(csv.DictReader(open(C/'pg_boxes.csv')));std=collections.defaultdict(list);extra=collections.defaultdict(list);oldmac=[q for q in csv.DictReader(open(C/'instances.csv')) if q['kind']=='macro'];samplelo,samplehi=4320,12960
for q in pg:
 if q['kind']=='metal':ls=[q['layer']]
 else:
  pairs=re.findall(r'VIA([1-9])([1-9])',q['via']) or re.findall(r'via([1-9])_([1-9])_',q['via']);assert len(pairs)==1,q['via'];ls=['M'+a for a in pairs[0]]
 box=np.array([int(q[k]) for k in ['x0_dbu','y0_dbu','x1_dbu','y1_dbu']]);cx,cy=(box[0]+box[2])/2,(box[1]+box[3])/2
 for layer in ls:
  if layer not in ['M2','M3','M4','M5']:continue
  margin=27 if layer in ['M2','M3'] else 36;b=box+np.array([-margin,-margin,margin,margin])
  if b[1]<samplehi and b[3]>samplelo:std[layer].append(b)
  if layer=='M5' and q['kind']=='via':
   for old in oldmac:
    x0,y0,w0,h0=[float(old[k])*1000 for k in ['x','y','w','h']]
    if x0<=cx<=x0+w0 and y0<=cy<=y0+h0:
     new=news[old['name']];dx,dy=new['x']*1000-x0,new['y']*1000-y0;extra[layer].append(b+np.array([dx,dy,dx,dy]));break
std={k:np.array(v) for k,v in std.items()};extra={k:np.array(v) for k,v in extra.items()};cuts=[];boxes=np.array(G._net_boxes(D));mm=[c for c in D.cells.values() if c[0]=='M']
def mask_free(t,lo,hi):
 delta=np.zeros(len(t)+1,dtype=np.int32);a=np.searchsorted(t,lo,'left');b=np.searchsorted(t,hi,'right');np.add.at(delta,a,1);np.add.at(delta,b,-1);return np.cumsum(delta)[:-1]==0

def source_phase_cap(direction,cut,nb):
 out=np.zeros(nb);ci=cut*1000
 for layer in (['M3','M5'] if direction=='V' else ['M2','M4']):
  if direction=='H':
   source_x=ci+8640;sy=np.array([y for y in tracks[layer]['Y'] if samplelo<=y<samplehi]);rs=std[layer];sel=(rs[:,0]<source_x)&(rs[:,2]>source_x);free=mask_free(sy,rs[sel,1],rs[sel,3]);ty=np.concatenate([sy+k*8640 for k in range(-1,36)]);ff=np.tile(free,37);ok=(ty>=0)&(ty<302400);t=ty[ok];free=ff[ok]
   for m in mm:
    if (m[2]-.036)*1000<ci<(m[4]+.036)*1000:free &= ~((t>(m[3]-.036)*1000)&(t<(m[5]+.036)*1000))
  else:
   source_y=samplelo+((ci-8640-samplelo)%8640);tx=np.array(tracks[layer]['X']);ok=(tx>=8640)&(tx<241920);source_t=tx[ok];t=source_t-8640;rs=std[layer];sel=(rs[:,1]<source_y)&(rs[:,3]>source_y);free=mask_free(source_t,rs[sel,0],rs[sel,2])
   if layer=='M3':
    for m in mm:
     if (m[3]-.027)*1000<ci<(m[5]+.027)*1000:free &= ~((t>(m[2]-.027)*1000)&(t<(m[4]+.027)*1000))
   if layer in extra:
    es=extra[layer];sel=(es[:,1]<ci)&(es[:,3]>ci);free &= mask_free(t,es[sel,0],es[sel,2])
  bins=(t[free]/1000).astype(int);bins=bins[(bins>=0)&(bins<nb)];out+=np.bincount(bins,minlength=nb)*G.TRACK_DERATE
 lo,hi=(boxes[:,1],boxes[:,3]) if direction=='V' else (boxes[:,0],boxes[:,2]);crossings=int(((lo<cut)&(hi>cut)).sum());cuts.append(dict(direction=direction,cut_um=cut,derived_PG_tracks=float(out.sum()),source_net_boxes=crossings,whole_cut_ratio=crossings/max(float(out.sum()),1)))
 return out
src=inspect.getsource(G.demand_metrics).replace('def demand_metrics(', 'def predicted_demand(').replace('cap = np.full(nb, full * step)','cap = source_phase_cap(d,float(c),nb)');ns=dict(vars(G));ns['source_phase_cap']=source_phase_cap;exec(src,ns);predicted=ns['predicted_demand'](D)
r=dict(status='NEW_GEOMETRY_SOURCE_MODEL_NOT_NEW_NATIVE_FP_OR_PLACE',outline_um=[233.28,302.4],source_cells=len(D.cells),source_nets=len(D.nets),FFs=len(poses),R2R=rr,pins=pr,new_macro_new_pin_new_FF_nominal_cut_model=nominal,native_phase_PG_prediction=predicted,full_cuts=cuts,source_cell_mass_density_target=float(os.environ.get('COMB_DENSITY','0')),macro_views_unchanged=True,signal_ceiling='M5',added_cycles=0,limits=['Uses real current source nets, new6849pin map and new six-macro coordinates; FFs are source-local old/new-row intersection PREP','Combinational centers are analytical barycentric estimates, not detailed legalized placement','PG is a source-phase prediction from actual native macro-free row strip, plus translated real macro M5 PG contacts and complete LEF OBS; new native PG still OPEN','No threshold/track fraction/clock relaxation, no adoption or P&R permission'])
(O/'source_cut_model_PREP.json').write_text(json.dumps(r,indent=2)+'\n');(O/'source_cell_model_PREP.json.gz').write_bytes(gzip.compress(json.dumps(list(D.cells.values()),separators=(',',':')).encode(),mtime=0));print(json.dumps({k:v for k,v in r.items() if k not in ['full_cuts','limits']},indent=2))
