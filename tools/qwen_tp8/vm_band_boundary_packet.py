#!/usr/bin/env python3
"""Export exact regional launch/band capture pins and corner budgets for joint repair."""
import collections,gzip,hashlib,json,sys
from pathlib import Path
from vm_lef_pins import read
from vm_bay_cluster import VIEW
from vm_band_pair import timing
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
from pinreg_audit import parse_lib,clock_refs,pin_metrics
A=ROOT/'results/arch/qwen_tp8_1012'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 cf=A/'vm_band_composition_codex.json';pf=A/'vm_leaf_plan_claude.json';rf=A/'vm_band_paths_codex.json';bf=A/'vm_band_boundary_extension_codex.json'
 c=json.loads(cf.read_text());p=json.loads(pf.read_text());r=json.loads(rf.read_text());b=json.loads(bf.read_text())
 df=ROOT/r['all_bit_details']['path'];assert sha(cf)==r['source_sha256'] and sha(df)==r['all_bit_details']['sha256']
 bays={v['n']:v for v in p['x_relay_bays']};cs={(v['bay'],v['slot']):v for v in c['children'] if 'bay'in v}
 must=set(b['necessary_geometry_bound']['scenarios'][0]['unreachable_launch_lane_names']);cache={};hashes={}
 def table(view,corner):
  key=(view,corner)
  if key not in cache:
   vd=ROOT/view;f=next(vd.glob(f'*_{corner}.lib'));ins=vd/'insertion.json'
   parsed=parse_lib(f);refs=clock_refs(parsed,json.loads(ins.read_text()),corner)
   cache[key]=(pin_metrics(parsed,refs),refs);hashes[str(f.relative_to(ROOT))]=sha(f);hashes[str(ins.relative_to(ROOT))]=sha(ins)
  return cache[key]
 def side(view,pin,corner):
  m,refs=table(view,corner);z=m[pin];ref=refs[z['clk'][0]]
  return dict(view=view,pin=pin,clock=z['clk'][0],R_ps=ref['rise'],boundary_min_ps=ref['bmin'],boundary_max_ps=ref['bmax'],
   o_ps=None if z['out']is None else z['out']+ref['bmax']-ref['rise'],
   s_ps=None if z['inp']is None else z['inp']+ref['rise']-ref['bmin'],
   l_ps=None if z['lmin']is None else z['lmin']+ref['bmin']-ref['rise'],
   h_ps=None if z['hold']is None else z['hold']+ref['rise']-ref['bmax'])
 edges=[];regions=collections.Counter();badregions=collections.Counter()
 for e in json.load(gzip.open(df,'rt'))['edges']:
  if e['kind']!='regional_boundary_lower_bound':continue
  l=e['launch'];cap=e['capture'];region=bays[l['bay']]['region'];regions[region]+=1
  if e['lane']in must:badregions[region]+=1
  lv=VIEW[l['kind']];cv=cs[cap['bay'],cap['slot']]['view'];lb=l['bit0']+e['bit'];cb=cap['bit0']+cap.get('bit_permutation',list(range(8)))[e['bit']]
  budgets={}
  for corner in ('tt','ff','ss'):
   ls=side(lv,f'q[{lb}]',corner);ss=side(cv,f'd[{cb}]',corner)
   skew=90 if max(ls['R_ps'],ss['R_ps'])<=300 else 150
   available=833.3333333333-60-skew;zero=available-ls['o_ps']-ss['s_ps']
   budgets[corner]=dict(launch=ls,capture=ss,available_ps=available,zero_wire_setup_slack_ps=zero,
    reach_at_TT_wire_coefficient_um=min(500,zero/.76),deep_entry_zero_wire_setup_slack_ps=833.3333333333-210-ls['o_ps']-ss['s_ps'],deep_entry_reach_at_TT_wire_coefficient_um=min(500,(833.3333333333-210-ls['o_ps']-ss['s_ps'])/.76),
    FF_hold_with_ideal_wire_credit_ps=None if corner!='ff' else ls['l_ps']-ss['h_ps']+.112*e['length_um']-100)
  edges.append(dict(lane=e['lane'],bit=e['bit'],region=region,must_move_launch_constraint=e['lane']in must,
    launch_stage=l,capture_stage=cap,launch_xy_um=e['A'],capture_xy_um=e['B'],length_um=e['length_um'],corner_budgets=budgets))
 # Complete P2 candidate pin arrays let the region worker evaluate actual new relay pairs.
 pv=VIEW['P'];lef=next((ROOT/pv).glob('*.lef'));pins=read(lef)[1];hashes[str(lef.relative_to(ROOT))]=sha(lef)
 p2={port:[dict(bit=i,xy_um=[pins[f'{port}[{i}]']['x'],pins[f'{port}[{i}]']['y']],corners={co:side(pv,f'{port}[{i}]',co) for co in ('tt','ff','ss')}) for i in range(480)] for port in ('d','q')}
 relay_pins={}
 for kind in ('E','W'):
  view=VIEW[kind];lf=next((ROOT/view).glob('*.lef'));rp=read(lf)[1];hashes[str(lf.relative_to(ROOT))]=sha(lf)
  relay_pins[kind]={port:[dict(bit=i,xy_um=[rp[f'{port}[{i}]']['x'],rp[f'{port}[{i}]']['y']],corners={co:side(view,f'{port}[{i}]',co)for co in ('tt','ff','ss')})for i in range(512)]for port in ('d','q')}
 detail=dict(boundary_edges=edges,P2_actual_pins=p2,one_stage_relay_actual_pins=relay_pins)
 out=A/'vm_band_boundary_packet_codex.json.gz'
 with gzip.open(out,'wt')as f:json.dump(detail,f,separators=(',',':'))
 summary=dict(schema='opentallas.qwen.vm-band-joint-boundary-packet.v1',qualification=False,all_boundary_bits=len(edges),
  bits_by_regional_owner=dict(regions),must_move_constraint_bits_by_owner=dict(badregions),must_move_lane_names=sorted(must),
  source_hashes={str(f.relative_to(ROOT)):sha(f)for f in (cf,pf,rf,bf,df)},view_hashes=hashes,
  packet=dict(path=str(out.relative_to(ROOT)),sha256=sha(out)),spare_slots=b['spare_whole_slots'],
  semantics='TT setup is authoritative existing pair gate. FF/SS exported exact sides; reach with .76 is explicitly TT-wire-coefficient screening, not corner signoff. FF hold uses ideal .112 wire credit; real routed hold remains required.',
  requirements=['Keep lane/visit/bit and bank-major consumer mapping; no bus-order inference.','Joint move must check predecessor/internal region links as well as this boundary; candidate-only until all-corner feasibility.','P2 carries two enabled stages; load_step/loader advances independent of paused core_step; held q_v requires fill-fire/token consumption.'])
 (A/'vm_band_boundary_packet_codex.json').write_text(json.dumps(summary,indent=1)+'\n')
 print(dict(all_bits=len(edges),regions=dict(regions),must_move_bits_by_owner=dict(badregions),packet=str(out)))
if __name__=='__main__':main()
