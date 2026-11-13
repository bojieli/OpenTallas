from pathlib import Path
import importlib.util,json,math,argparse
ap=argparse.ArgumentParser(description='Refine blanket M6 OBS above tiny M5 S/N boundary pins using exact metal; no real metal removed.');ap.add_argument('--base',required=True);ap.add_argument('--detail',required=True);ap.add_argument('--out',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--tool',default=str(Path(__file__).resolve().parents[3]/'tools/die_plan/abstract_detail.py'));args=ap.parse_args()
spec=importlib.util.spec_from_file_location('AD',args.tool);A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
base=Path(args.base);b=base.read_text().splitlines(keepends=True);wh=A._size_wh(b);wins={}
for pin,shapes in A._signal_pin_shapes(b).items():
 for layer,r in shapes:
  if layer=='M5' and r[2]-r[0]<=.03 and r[3]-r[1]<=.1 and min(r[1],wh[1]-r[3])<=.001:
   wins[pin]=dict(layer=layer,rect=list(A._grow(r,1.,wh)),layers=['M6']);break
# Spatial index avoids quadratic exact-metal/window comparisons on production-width boundary buses.
idx={}
for pin,w in wins.items():
 r=w['rect']
 for i in range(math.floor(r[0]/2),math.floor(r[2]/2)+1):idx.setdefault(i,[]).append(pin)
exact=Path(args.detail);metal={};seen=set();cnt=0
for line in A._iter_obs_layers(exact,{'M6'}).get('M6',[]):
 m=A._RECT.match(line)
 if not m:continue
 r=tuple(float(v) for v in m.groups()[1:]);cnt+=1
 # Every selected window touches S or N; reject the core interior in constant time.
 if r[1]>1.084 and r[3]<wh[1]-1.084:continue
 cand=set()
 for i in range(math.floor(r[0]/2),math.floor(r[2]/2)+1):cand.update(idx.get(i,()))
 for pin in cand:
  h=wins[pin]['rect'];c=(max(r[0],h[0]),max(r[1],h[1]),min(r[2],h[2]),min(r[3],h[3]))
  if c[2]>c[0]+1e-9 and c[3]>c[1]+1e-9:seen.add(c)
if seen:metal['M6']=sorted(seen)
new,cut=A.apply_windows(b,wins,metal);window=dict(margin_um=1.,top_layer='M6',clear_um=.05,windows=wins,cut=cut,window_detail=str(exact),window_detail_sha256=A._sha(exact),window_detail_signal_pin_geometry_equal_base=A._signal_pin_shapes(A._head_stream(exact))==A._signal_pin_shapes(b),base_kind='provisional plan-contract LEF, preserves its header and PG pins byte-for-byte')
ok,probs=A.check(b,new,[],window);ok=ok and window['window_detail_signal_pin_geometry_equal_base'];p=Path(args.out);p.write_text(''.join(new));rep=dict(status='PRIVATE_DIAGNOSTIC_VIEW_NOT_ADOPTED',base=str(base),out=str(p),check_ok=ok,problems=probs,layers_detailed=[],class_name='M5 tiny S/N boundary pins with alternate M6 via access',pin_window=window)
Path(args.receipt).write_text(json.dumps(rep,indent=1)+'\n');print(json.dumps(dict(check_ok=ok,pins=len(wins),cut=cut,exact_m6_rects_scanned=cnt,exact_m6_rects_restored=len(seen),problems=probs)))
assert ok and window['window_detail_signal_pin_geometry_equal_base'],probs
