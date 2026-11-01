from pathlib import Path
import json,re
r=Path(__file__).resolve().parent;ctx=json.load(open(r/'NE_feed_context.json'));d=(r/'NE_feed_crop.def').read_text()
# Keep every original layer blockage and PG/mesh stripe. Replace only diagnostic components/nets/ports.
def section(s,name,body):return re.sub(rf'(?ms)^{name} \d+ ;.*?^END {name}',body,s)
for label,src,invert in [('a','ck_b819',False),('b','ck_r821_0',True)]:
 for mode in ('old','new'):
  out=r/f'feed_ne_{label}_{mode}';out.mkdir(exist_ok=True)
  cells=ctx[src];lines=[]
  for n,c in cells.items():
   x,y=c['xy'];x-=15042.24;y-=6065.28
   lines.append(f'- {n} {c["master"]} + FIXED ( {round(x*1000)} {round(y*1000)} ) N ;')
  if mode=='new' and invert:lines.append('- restore CKINVDCx16_ASAP7_75t_R + FIXED ( 4434480 630720 ) N ;')
  s=section(d,'COMPONENTS',f'COMPONENTS {len(lines)} ;\n'+'\n'.join(lines)+'\nEND COMPONENTS')
  x,y=cells[src]['xy'];x=round((x-15042.24-1.0)*1000);y=round((y-6065.28)*1000)
  pins=[f'- drive + NET input + DIRECTION INPUT + USE CLOCK + LAYER M9 ( -40 -40 ) ( 40 40 ) + FIXED ( {x} {y} ) N ;']
  if mode=='new':pins.append('- mesh_root + NET '+('bridge' if invert else 'feed')+' + DIRECTION OUTPUT + USE CLOCK + LAYER M9 ( -40 -40 ) ( 40 40 ) + FIXED ( 4449640 630720 ) N ;')
  if 'PINS' not in s:s=s.replace('COMPONENTS',f'PINS {len(pins)} ;\n'+'\n'.join(pins)+'\nEND PINS\nCOMPONENTS',1)
  loads=' '.join(f'( {n} A )' for n in cells if n!=src)
  nets=[f'- input ( PIN drive ) ( {src} A ) + USE CLOCK ;',f'- feed ( {src} Y ) '+loads+(' ( restore A )' if mode=='new' and invert else ' ( PIN mesh_root )' if mode=='new' else '')+' + USE CLOCK ;']
  if mode=='new' and invert:nets.append('- bridge ( restore Y ) ( PIN mesh_root ) + USE CLOCK ;')
  s=section(s,'NETS',f'NETS {len(nets)} ;\n'+'\n'.join(nets)+'\nEND NETS')
  (out/'pilot.def').write_text(s)
  (out/'meta.json').write_text(json.dumps(dict(variant=label,source=src,mode=mode,restore=invert and mode=='new',source_normal_polarity=not invert,root_um=[4449.64,630.72],source_xy_um=[c-ori for c,ori in zip(cells[src]['xy'],[15042.24,6065.28])],old_source_sinks=[n for n in cells if n!=src])))
