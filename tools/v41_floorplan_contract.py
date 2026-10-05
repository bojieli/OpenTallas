"""Generate a geometric reservation plan; no macro packing or timing closure claim."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build():
 source=ROOT/'results/arch/v41_die_assembly.json'
 d=json.loads(source.read_text())['floorplan']['layer'];w,h=d['die_w_mm'],d['die_h_mm']
 # Package-edge envelopes inherited from analytical model; internal partition is proposed.
 rects=[]
 def add(name,x,y,dx,dy,kind):rects.append(dict(name=name,x_mm=x,y_mm=y,w_mm=dx,h_mm=dy,kind=kind))
 add('south_HBM_and_controller_reservation',1,0,w-2,2,'io')
 add('north_HBM_and_controller_reservation',1,h-2,w-2,2,'io')
 add('west_external_links',0,0,1,h,'io');add('east_package_link',w-1,0,1,h,'io')
 # Explicit corridors; never compress regions to make content fit.
 add('horizontal_registered_transport',1,h/2-.4,w-2,.8,'channel')
 add('vertical_registered_transport',w/2-.4,2,.8,h/2-2.4,'channel')
 add('vertical_registered_transport_north',w/2-.4,h/2+.4,.8,h/2-2.4,'channel')
 dx=(w-2-.8)/2;dy=(h-4-.8)/2
 for row,y in enumerate((2,h/2+.4)):
  for col,x in enumerate((1,w/2+.4)):
   add(f'local_compute_memory_region_{row*2+col}',x,y,dx,dy,'compute')
 return dict(schema='v41.floorplan.reservations.v1',status='proposed_reservations_not_macro_fit',objective_order=['minimize_single_user_complete_token_latency','maximize_independent_user_pipeline_throughput_without_regressing_primary'],die_mm=[w,h],source_sha256={str(source.relative_to(ROOT)):hashlib.sha256(source.read_bytes()).hexdigest()},regions=rects,macro_packing_verified=False,clock_hz_verified=None,token_rate=None,unresolved=['per_region_complete_macro_and_logic_fit','actual_HBM_PHY_geometry_and_package_bump_map','routing_track_capacity_and_pin_assignment','per_edge_pipeline_delay_and_clock_crossing','PDN_IR_EM_and_clock_distribution','power_per_region_and_thermal_density','integer_tensor_expert_placement','full_token_dependency_schedule'])
def validate(d):
 w,h=d['die_mm'];rs=d['regions']
 for r in rs:
  assert min(r['x_mm'],r['y_mm'])>=0 and min(r['w_mm'],r['h_mm'])>0
  assert r['x_mm']+r['w_mm']<=w+1e-8 and r['y_mm']+r['h_mm']<=h+1e-8
 for i,a in enumerate(rs):
  for b in rs[i+1:]:
   overlap_x=min(a['x_mm']+a['w_mm'],b['x_mm']+b['w_mm'])-max(a['x_mm'],b['x_mm'])
   overlap_y=min(a['y_mm']+a['h_mm'],b['y_mm']+b['h_mm'])-max(a['y_mm'],b['y_mm'])
   assert overlap_x<=1e-8 or overlap_y<=1e-8,(a['name'],b['name'])
 assert abs(sum(r['w_mm']*r['h_mm'] for r in rs)-w*h)<1e-6
 assert not d['macro_packing_verified'] and d['token_rate'] is None
 return d
def main():
 d=validate(build());out=ROOT/'results/floorplan';out.mkdir(exist_ok=True)
 (out/'v41_reservation_plan.json').write_text(json.dumps(d,indent=2)+'\n')
 w,h=d['die_mm'];scale=25;svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w*scale} {h*scale+65}">','<rect width="100%" height="100%" fill="white"/>','<text x="10" y="18" font-family="sans-serif" font-size="13">V4.1 provisional reservations — NOT macro fit or timing closure</text>']
 for r in d['regions']:
  x,y=r['x_mm']*scale,r['y_mm']*scale+35;dx,dy=r['w_mm']*scale,r['h_mm']*scale
  color={'io':'#dce7f5','channel':'#f7dfad','compute':'#dceede'}[r['kind']]
  svg.append(f'<rect x="{x}" y="{y}" width="{dx}" height="{dy}" fill="{color}" stroke="#333" stroke-width="0.6"/>')
  if r['kind']=='compute':svg.append(f'<text x="{x+8}" y="{y+22}" font-family="sans-serif" font-size="12">{r["name"]}</text>')
 svg.append('</svg>');(out/'v41_reservation_plan.svg').write_text('\n'.join(svg))
if __name__=='__main__':main()
