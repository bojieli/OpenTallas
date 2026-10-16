#!/usr/bin/env python3
"""Source-bound SM single-row lower bounds, not a physical qualification.
Actual existing tile outlines and FC/BE LEFs are read, never shrunk. Soft static
front, all pins/clock delivery, relays and cut capacity remain explicit OPENs.
"""
import hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[2]
def lef(path):
 p=ROOT/path;t=p.read_text();m=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',t)
 return dict(path=path,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),outline_um=[float(m[1]),float(m[2])])
def main():
 out=ROOT/'results/arch/hbm_sm_repack_1015/single_row_2330';out.mkdir(parents=True,exist_ok=True)
 fc={}
 for n,s in [('xl','smh_fcxl_ref_p45'),('tw','smh_fct_ref_p45'),('rw','smn_fcxr_ref_fa'),('bw','smh_fcb_ref_p45')]:
  cell={'xl':'xl','tw':'t','rw':'xr','bw':'b'}[n]
  paths=list((ROOT/'physical/ref_tile'/s/'views').glob('**/*.lef'))
  if not paths:
   paths=list((ROOT/'physical/ref_tile').glob('*/views/ot_hbm_accel_smh_fc_'+cell+'/*.lef'))
  if not paths: paths=list((ROOT/'physical/hbm_accel_smh_views').glob('fc_hier/*/ot_hbm_accel_smh_fc_'+cell+'/*.lef'))
  if not paths: raise RuntimeError('No actual FC view '+n)
  fc[n]=lef(str(paths[0].relative_to(ROOT)))
 be=lef('physical/ref_tile/smn_be_eg_ref/views/ot_hbm_accel_smh_be_eg/ot_hbm_accel_smh_be_eg.lef')
 candidates=[]
 for name,tw,th in [('rp2',397.44,1330.56),('rp3',406.08,1192.32)]:
  body=16*tw+15*21.6
  candidates.append(dict(tile=name,tile_outline_um=[tw,th],single_row_body_lower_bound_um=[round(body,3),th],
   old_slot_um=[6609.6,1712.08],body_exceeds_slot_width_um=round(body-6609.6,3),
   old_centerfront_width_um=345.6,with_centerfront_lower_bound_um=round(body+345.6+21.6,3),
   two_row_reference_um=[round(8*(tw+21.6)+345.6,3),round(2*th+77.76+43.2,3)],
   pair_adjacent_horizontal_logical_hop_lower_bound_um=round(2*(tw+21.6)-tw,3),
   note='Horizontal p0/p1 chains skip the other tile of each pair. This number is edge distance only; actual face-pin endpoints/face transit may be farther.'))
 d=dict(schema='opentallas.sm_single_row_lower_bound.v1',source_scope='geometric lower bound, no slot change or qualification',
  actual_fc_views=fc,actual_be_view=be,candidates=candidates,
  retired_children_excluded=['front_n','front_s','fc_bc','fc_is'],
  actual_static_front='rtl/hbm_accel/sm/static/ot_smh_static_front.sv: xl,tw,te,rw,re,bw,be plus u_feed and soft pipeline/deskew registers',
  graph_constraints=[
   'Eight columns by two tiles is a 2-D graph. Flattening to one row requires actual path/relay and fixed-cycle compiler repair.',
   'Pair-adjacent order preserves gather adjacency if one tile is MX, but each horizontal row chain skips one tile. Existing logical latency cannot be inherited.',
   'Ordering all p0 then all p1 preserves horizontal chains but makes many gather hops millimeters long.',
   'Front strip above tiles is a candidate; actual feed synthesis, port demand and all incident routes must fit the remaining height.',
   'Clock roots must remain independent at each child entry with measured insertion compensation.'],
  qualification_open=['static-front real synthesis and hardening','all pin locations/orientations','all incident exact path graph','relay homes and extra calendar cycles','cut capacity and trial GRT','native clock timing','full functional and throughput proof'])
 (out/'bounds.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
if __name__=='__main__':main()
