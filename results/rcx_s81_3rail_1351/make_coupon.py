from pathlib import Path
import json, math, hashlib
R=Path(__file__).resolve().parent
full=R/'input/graded_metal.json'
if full.exists():
 j=json.loads(full.read_text());source_hash=hashlib.sha256(full.read_bytes()).hexdigest();xs=j['xs'][93:99];ys=j['ys'][93:99]
else:
 selected=json.loads((R/'selected_geometry.json').read_text());j=selected;source_hash=selected['source_sha256'];xs=selected['xs_global_um'];ys=selected['ys_global_um']
x0=min(xs)-10;y0=min(ys)-10
inside=lambda x,y:min(xs)-.001<=x<=max(xs)+.001 and min(ys)-.001<=y<=max(ys)+.001
segs=[s for s in j['segments'] if inside(*s['centre_um'][:2]) and inside(*s['centre_um'][2:])]
vias=[v for v in j['vias'] if inside(v['x_um'],v['y_um'])]
widths=sorted({s['width_um'] for s in segs})
if widths != [1.6,1.68,1.76]:raise ValueError(('unexpected actual widths',widths))
(R/'coupon').mkdir(exist_ok=True);out=R/'coupon'
db=lambda v:round(v*1000)
xy=lambda x,y:(db(x-x0),db(y-y0))
W=max(xs)-x0+10;H=max(ys)-y0+10
pins=[]
for name,x,y in [('src',xs[0],ys[1]),('sink',xs[-1],ys[-2])]:
 a,b=xy(x,y);pins.append(f'- {name} + NET ck_mesh + DIRECTION INPUT + USE CLOCK + LAYER M8 ( -40 -40 ) ( 40 40 ) + FIXED ( {a} {b} ) N ;')
pg={'VDD':[],'VSS':[]}
for lay,lo,hi in [('M8',y0,y0+H),('M9',x0,x0+W)]:
 for n in range(math.floor((lo-4.32)/8.64)-1,math.ceil((hi-4.32)/8.64)+2):
  c=4.32+n*8.64
  if not lo+.24<=c<=hi-.24:continue
  a,b=(xy(x0,c),xy(x0+W,c)) if lay=='M8' else (xy(c,y0),xy(c,y0+H))
  pg['VDD' if n%2==0 else 'VSS'].append(f'NEW {lay} 480 + SHAPE STRIPE ( {a[0]} {a[1]} ) ( {b[0]} {b[1]} )')
lines=['VERSION 5.8 ;','DIVIDERCHAR "/" ;','BUSBITCHARS "[]" ;','DESIGN s81_3rail_coupon ;','UNITS DISTANCE MICRONS 1000 ;',f'DIEAREA ( 0 0 ) ( {db(W)} {db(H)} ) ;','PINS 2 ;',*pins,'END PINS','SPECIALNETS 2 ;']
for net,shapes in pg.items():
 shapes[0]=shapes[0].replace('NEW','+ ROUTED',1);lines += [f'- {net} ( * {net} ) + USE '+('POWER' if net=='VDD' else 'GROUND'),*shapes,';']
lines += ['END SPECIALNETS','NETS 1 ;','- ck_mesh ( PIN src ) ( PIN sink ) + USE CLOCK ;','END NETS','END DESIGN']
(out/'coupon.def').write_text('\n'.join(lines)+'\n')
t=['read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef','read_def /out/coupon.def','set tech [ord::get_db_tech]','set blk [ord::get_db_block]','proc LY {n} {global tech;return [$tech findLayer $n]}']
for w in widths:t.append(f'create_ndr -name w{db(w)} -width {{M8 {w} M9 {w}}} -spacing {{M8 1.0 M9 1.0}}')
t += ['set net [$blk findNet ck_mesh]','set wire [odb::dbWire_create $net]','set e [odb::dbWireEncoder]','$e begin $wire']
for s in segs:
 lay=s['layer'];a,b=xy(*s['centre_um'][:2]);c,d=xy(*s['centre_um'][2:]);w=db(s['width_um'])
 t += [f'$e newPath [LY {lay}] FIXED [[$blk findNonDefaultRule w{w}] getLayerRule [LY {lay}]]',f'$e addPoint {a} {b}',f'$e addPoint {c} {d}']
for n,v in enumerate(vias):
 rows,cols=v['rows'],v['cols'];cut=v['cut_um'];pit=v['pitch_um'];pad=v['pad_um'];hx=(cols-1)*pit/2+cut/2;hy=(rows-1)*pit/2+cut/2
 t += [f'set v [odb::dbVia_create $blk va{n}]',f'odb::dbBox_create $v [LY M8] {-db(pad/2)} {-db(pad/2)} {db(pad/2)} {db(pad/2)}',f'odb::dbBox_create $v [LY M9] {-db(pad/2)} {-db(pad/2)} {db(pad/2)} {db(pad/2)}']
 for i in range(rows):
  for k in range(cols):
   a=-hx+k*pit;b=-hy+i*pit;t.append(f'odb::dbBox_create $v [LY V8] {db(a)} {db(b)} {db(a+cut)} {db(b+cut)}')
 a,b=xy(v['x_um'],v['y_um']);t += ['$e newPath [LY M8] FIXED',f'$e addPoint {a} {b}','$e addVia $v']
t += ['$e end','write_db /out/coupon.odb','write_def /out/actual.def']
(out/'build.tcl').write_text('\n'.join(t)+'\n')
record={'source_sha256':source_hash,'source_global_origin_um':[x0,y0],'xs_global_um':xs,'ys_global_um':ys,'segments':segs,'vias':vias,'widths_um':widths,'pg':{'width_um':.48,'pitch_um':8.64,'offset_um':4.32,'global_phase_preserved':True},'scope':'native RCX coupon only; not die route/STA; whole plan BLOCKED'}
(out/'geometry.json').write_text(json.dumps(record,indent=1)+'\n')
print('segments',len(segs),'vias',len(vias),'widths',widths,'extent',W,H)
