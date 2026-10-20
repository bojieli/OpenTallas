#!/usr/bin/env python3
"""Owned M3/M4 escape aprons from immutable SYSFACE core contacts to p192 faces.

Distinct analytical masters. Original core, behavior, and all original views stay
immutable. Every new terminal has an explicit route to an original LEF contact;
no assumption that internal core ports move. No parent/DRC/timing qualification.
"""
import copy, dataclasses, hashlib, json, math, re, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import asap7, rom_gen as R, sram_gen as S
from views import Timing, write_liberty
ROOT=Path(__file__).resolve().parents[2]
ORIGINALS=['ot_sram_1r1w_64x16_m1','ot_rom_4096x72_m8']
# Native VIA34: M3 +/-9x17nm, M4 +/-20x12nm, V3 +/-9x12nm.
VIA={'M3':[-9,-17,9,17],'M4':[-20,-12,20,12],'V3':[-9,-12,9,12]}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pinblocks(s):
 return list(re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1(?=\s|$)',s,re.S))
def rects(b):
 return [list(map(lambda x:round(float(x)*1000),m)) for m in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',b)]
def compile_one(old,out):
 src=ROOT/'physical/asap7_memory_macros'/old; meta=json.loads((src/(old+'.json')).read_text()); lef=(src/(old+'.lef')).read_text()
 ow,oh=[round(float(x)*1000) for x in re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)\s*;',lef).groups()]
 signals=[];pg=[]
 for m in pinblocks(lef):
  name,body=m.groups();rr=rects(body)
  if re.search(r'USE\s+(POWER|GROUND)',body):pg.append((name,rr));continue
  assert len(rr)==1,(name,rr)
  r=rr[0];assert r[0]==0 or r[2]==ow,(name,r)
  signals.append({'name':name,'direction':re.search(r'DIRECTION\s+(\S+)',body).group(1),'clock':'USE CLOCK' in body,'rect':r,'face':'W' if r[0]==0 else 'E'})
 faces={f:sorted([p for p in signals if p['face']==f],key=lambda p:p['rect'][1]) for f in ['W','E']}
 n=max(map(len,faces.values()));apron=(n+2)*108;w=ow+2*apron;h=oh
 assert w%36==0
 name=old+'_escape_p192';d=out/name;d.mkdir(parents=True,exist_ok=True)
 shapes=[];vias=[];routes=[];external=[]
 for face,pins in faces.items():
  for i,p in enumerate(pins):
   yold=(p['rect'][1]+p['rect'][3])//2; ynew=(pins[0]['rect'][1]+pins[0]['rect'][3])//2+i*192
   assert ynew+12<h-20
   col=(i+1)*108; anchor=apron+24
   # In left-face coordinates: old horizontal leg reaches true old contact;
   # new leg reaches outer face; monotone columns keep coincident-y legs apart.
   rr=[('M4',[0,ynew-12,col+20,ynew+12]),('M4',[col-20,yold-12,anchor,yold+12])]
   if yold!=ynew:rr.append(('M3',[col-9,min(yold,ynew)-17,col+9,max(yold,ynew)+17]))
   for layer,r in rr:
    if face=='E':r=[w-r[2],r[1],w-r[0],r[3]]
    shapes.append({'net':p['name'],'layer':layer,'rect_nm':r})
   if yold!=ynew:
    for y in [yold,ynew]:
     x=col if face=='W' else w-col
     vias.append({'net':p['name'],'via':'VIA34','xy_nm':[x,y]})
     for layer,r in VIA.items():shapes.append({'net':p['name'],'layer':layer,'rect_nm':[x+r[0],y+r[1],x+r[2],y+r[3]]})
   # Zero vertical length needs no via. Both M4 legs then form one conductor.
   er=[0,ynew-12,24,ynew+12] if face=='W' else [w-24,ynew-12,w,ynew+12]
   external.append((p,er));routes.append({'net':p['name'],'face':face,'old_contact_nm':[x+(apron if j%2==0 else 0) for j,x in enumerate(p['rect'])],'external_rect_nm':er,'m4_length_um':apron/1000,'m3_length_um':abs(ynew-yold)/1000,'via_count':0 if ynew==yold else 2})
 # Include translated original supply geometry in the finite short check;
 # source core contents below its original OBS remain immutable and opaque.
 for net,rr in pg:
  for r in rr:shapes.append({'net':net,'layer':'M4','rect_nm':[r[0]+apron,r[1],r[2]+apron,r[3]]})
 bad=[]
 for i,a in enumerate(shapes):
  for b in shapes[i+1:]:
   if a['net']==b['net'] or a['layer']!=b['layer']:continue
   x=a['rect_nm'];y=b['rect_nm']
   if min(x[2],y[2])>max(x[0],y[0]) and min(x[3],y[3])>max(x[1],y[1]):bad.append([a,b])
 assert not bad,('cross-net intersection',bad[:1])
 L=['VERSION 5.7 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {name}',f'  SIZE {w/1000:.3f} BY {h/1000:.3f} ;','  CLASS BLOCK ;']
 for p,r in external:
  L += [f'  PIN {p["name"]}',f'    DIRECTION {p["direction"]} ;','    USE CLOCK ;' if p['clock'] else '    USE SIGNAL ;','    PORT','      LAYER M4 ;','      RECT '+' '.join(f'{x/1000:.3f}' for x in r)+' ;','    END',f'  END {p["name"]}']
 for net,rr in pg:
  L += [f'  PIN {net}','    DIRECTION INOUT ;','    USE '+('POWER' if net=='VDD' else 'GROUND')+' ;','    PORT','      LAYER M4 ;']
  L += ['      RECT '+' '.join(f'{(x+(apron if j%2==0 else 0))/1000:.3f}' for j,x in enumerate(r))+' ;' for r in rr]
  L += ['    END',f'  END {net}']
 L+=['  OBS']
 for layer in ['M1','M2','M3']: L += [f'    LAYER {layer} ;',f'    RECT 0 0 {w/1000:.3f} {h/1000:.3f} ;']
 L += ['    LAYER M4 ;',f'    RECT 0.072 0 {(w-72)/1000:.3f} {h/1000:.3f} ;','  END',f'END {name}','END LIBRARY']
 (d/(name+'.lef')).write_text('\n'.join(L)+'\n')
 for suffix in ['.v','_bb.v']:
  (d/(name+suffix)).write_text((src/(old+suffix)).read_text().replace(old,name))
 spec=copy.deepcopy(meta['spec']);spec['name']=name
 pins=R.pins_for(R.RomSpec(**spec)) if meta['kind']=='rom' else S.pins_for(S.SramSpec(**spec))
 maxv=max(r['m3_length_um'] for r in routes); lh=apron/1000;r3,c3=asap7.SETRC['M3'];r4,c4=asap7.SETRC['M4'];cap=maxv*c3+lh*c4
 # Two native VIA34 cuts are explicit but no calibrated cut R/C exists in this
 # compiler: expose that dependency. Metal-only RC below is a lower-bound price.
 prices={}
 for corner in asap7.CORNERS:
  t=Timing(**copy.deepcopy(meta['timing'][corner]));delay=.38*(r3*maxv+r4*lh)*cap+max(t.out_r_kohm,asap7.calibration()['corners'][corner]['inv4_r_kohm'])*cap
  t.clk_to_q_ps+=delay;t.setup_ps+=delay;t.min_period_ps+=2*delay;t.min_pulse_ps=.4*t.min_period_ps;t.out_slew_intrinsic_ps+=delay;t.pin_cap_ff+=cap;t.clk_cap_ff+=cap
  t.read_energy_fj+=spec['bits']*cap*t.voltage**2;t.write_energy_fj+=spec['bits']*cap*t.voltage**2
  memory={'type':'rom' if meta['kind']=='rom' else 'ram','address_width':int(math.log2(spec['words'])),'word_width':spec['bits']}
  (d/(name+'_'+corner+'.lib')).write_text(write_liberty(name,t,pins,w*h/1e6,memory,'Analytical owned escape apron; uncharacterized VIA34 RC: NOT qualified'))
  prices[corner]={'metal_only_added_delay_ps':delay,'timing':dataclasses.asdict(t)}
 contract={'schema':'opentallas.owned_escape_apron.v1','master':name,'original':old,'source_sha256':{p.name:sha(p) for p in src.iterdir() if p.is_file()},'core_translation_nm':[apron,0],'core_dimensions_nm':[ow,oh],'outline_nm':[w,h],'side_apron_nm':apron,'orientation':'R0 only; no mirror qualification','external_pitch_nm':192,'column_pitch_nm':108,'native_via_geometry_nm':VIA,'owned_shapes':shapes,'owned_vias':vias,'routes':routes,'cross_net_overlap_count':len(bad),'original_area_um2':ow*oh/1e6,'area_um2':w*h/1e6,'added_cap_metal_only_ff':cap,'corners':prices,'hold':'unchanged old lower bound; no negative delay credit','qualification':'PROPOSAL_ONLY: VIA34 RC uncharacterized, spacing/EOL/native import, graph connectivity and real parent access/timing not qualified. Immutable old opaque core is connected at actual original contact rectangles, not retargeted. No actual production binding.'}
 (d/(name+'.json')).write_text(json.dumps(contract,indent=2)+'\n');print(name,'outline',w/1000,h/1000,'apron',lh,'added area',(w-ow)*h/1e6,'metal RC price',prices['tt']['metal_only_added_delay_ps'])
 return contract
if __name__=='__main__':
 out=ROOT/'physical/asap7_memory_macros'; reports=[compile_one(n,out) for n in ORIGINALS]
 print('SYSFACE 6 SRAM + 3 ROM macro area delta um2:',sum((r['area_um2']-r['original_area_um2'])*n for r,n in zip(reports,[6,3])))
