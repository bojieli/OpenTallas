"""Independent final native planning census, no EDA or kit writes."""
import json,csv,pathlib,math
R=pathlib.Path(__file__).parent;I=R/'input'
m=json.loads((R/'clock_model.json').read_text()); p=json.loads((I/'model.json').read_text());g=json.loads((I/'clock_entry_gate.json').read_text())
ff=list(csv.DictReader((I/'actual_FF_rows.csv').open()));W,H=p['outline_um']
def hit(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8
hard=[[a-4.32,b-4.32,c+4.32,d+4.32] for a,b,c,d in (x['rect_um'] for x in p['macros'])]
bodies=[[float(x['x_um'])-.702,float(x['y_um'])-.135,float(x['x_um'])+.702,float(x['y_um'])+.135] for x in ff]
errors=[];allids=[];maxradius=0
for i,q in enumerate(m['roots']):
 b=q['reservation_um'];x,y=q['xy_um']
 if not(b[0]>=4.32-1e-8 and b[1]>=4.32-1e-8 and b[2]<=W-4.32+1e-8 and b[3]<=H-4.32+1e-8):errors.append([i,'frame'])
 if abs((b[0]/2.16)-round(b[0]/2.16))>1e-7 or abs(b[1]/.27-round(b[1]/.27))>1e-7:errors.append([i,'native_row_grid'])
 if any(hit(b,t) for t in hard):errors.append([i,'macro_halo'])
 if any(hit(b,t) for t in bodies):errors.append([i,'actual_FF_body'])
 if any(hit(b,t['reservation_um']) for t in m['roots'][:i]):errors.append([i,'root_root'])
 if hit(b,g['entry_island_um']):errors.append([i,'entry_island'])
 ids=q['sink_indices'];allids.extend(ids)
 far=max(abs(s[k]-x)+abs(s[l]-y) for n in ids for s in [m['sinks'][n]['rect_um']] for k in (0,2) for l in (1,3))
 maxradius=max(maxradius,far)
 if far>220+1e-6 or len(ids)>1500 or not ids:errors.append([i,'radius_count',far,len(ids)])
assert sorted(allids)==list(range(20886))
entry=[]
for name,q in g['full_shapes'].items():
 b=q['rect_um'];x=(b[0]+b[2])/2;y=(b[1]+b[3])/2
 bad=[]
 if abs((x-.024)/.048-round((x-.024)/.048))>1e-6:bad.append('M5_track')
 if any(hit(b,t) for t in hard+bodies):bad.append('body_halo')
 if not(0<=b[0]<b[2]<=W and 0<=b[1]<b[3]<=H):bad.append('outline')
 # Regenerated native M5 pattern, both axis directions conservatively tested.
 # Not a receipt for a built grid or new-cell VDD/VSS binding.
 for ax in (0,1):
  for pol in (0,.192):
   for k in range(-2,math.ceil(max(W,H)/4.32)+2):
    c=4.32+2.064+pol+k*4.32
    if b[ax]<c+.06+.072-1e-8 and b[ax+2]>c-.06-.072+1e-8:bad.append('M5_pattern_axis'+str(ax));break
 entry.append(dict(name=name,rect_um=b,failures=bad))
 if bad:errors.append([name,bad])
out=dict(status='PASS_NATIVE_CLOCK_GEOMETRY_PREP' if not errors else 'FAIL_NATIVE_CLOCK_GEOMETRY_PREP',actual_unique_FF=len(ff),actual_unique_SRAM=len(p['macros']),matched_typed_clock_pins=len(m['sinks']),assigned_exactly_once=len(allids),regional_roots=len(m['roots']),max_load=max(x['sink_count'] for x in m['roots']),max_full_pin_L1_um=maxradius,margin_to_220_um=220-maxradius,root_grid_body_overlap_halo_failures=errors,entry=entry,scope='Full shape/source identity/landing geometry only; electrical CTS, actual built PDN connectivity, reset/START, arrival/skew, timing and physical adoption remain held')
(R/'audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
assert not errors
