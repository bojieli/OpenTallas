#!/usr/bin/env python3
"""Freeze source-supported pin/clock/reset identities for compressed tile adoption."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from screen_compressed_tile import load_pins,xy

def main():
 p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--reset',type=Path,required=True);p.add_argument('--views',type=Path,required=True);p.add_argument('--parent-repo',type=Path,required=True);p.add_argument('--boundaries',type=Path,required=True);p.add_argument('--prior-bundle',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 c=json.loads(a.candidate.read_text());d=json.loads(a.inventory.read_text());reset=json.loads(a.reset.read_text());allb=c['children']+c['banks']+c['reset_nodes'];assert len(allb)==c['expected_placed_bodies']==len({b['inst']for b in allb}), 'Candidate body arrays must be disjoint and complete';by={b['inst']:b for b in allb};old={b['inst']:b for b in d['children']+d['data_banks']+d['reset_nodes']};views={};hashes={};cost={}
 for b in allb:
  m=b['master']
  if m in views:continue
  path=a.parent_repo/b['view']/(m+'.lef')if b.get('kind')=='child'else a.views/m/'views'/m/(m+'.lef');blob=path.read_bytes();pins=load_pins(path,b['w'],b['h']);bc=a.boundaries/(m+'.json');boundary=json.loads(bc.read_text())['corners']['tt'];views[m]=dict(actual_LEF_text=blob.decode(),outline_um=[b['w'],b['h']],actual_LEF_pins=pins,TT_boundary=boundary);hashes[str(path)]=hashlib.sha256(blob).hexdigest();hashes[str(bc)]=hashlib.sha256(bc.read_bytes()).hexdigest()
 def pin(b,p):return xy(b,views[b['master']]['actual_LEF_pins'][p])
 def arc(b,p,role):
  v=views[b['master']]['TT_boundary'];cost=v['pins'].get(p,{}).get('O_minus_R_ps'if role=='o'else'S_plus_R_ps')
  return None if cost is None else(cost,v['R_ps'],v['clock_extrema_packet_ps']['launch'if role=='o'else'capture'])
 def screen(source,sp,sink,tp):
  v=arc(source,sp,'o');w=arc(sink,tp,'s')
  if v is None or w is None:return None
  L=sum(abs(x-y)for x,y in zip(pin(source,sp),pin(sink,tp)));margin=833.333-60-(150 if max(v[1],w[1])>300 else 90)-v[0]-w[0]-v[2]-w[2]-.76*L
  return dict(source=source['inst'],source_pin=sp,sink=sink['inst'],sink_pin=tp,source_xy=pin(source,sp),sink_xy=pin(sink,tp),distance_um=round(L,6),margin_ps=round(margin,6))
 tree=[]
 for r in reset['tree_legs']:
  if r['kind']=='global_input_to_root':continue
  source=by[r['source']];sink=by[r['sink']];z=screen(source,r['source_pin'],sink,r['sink_pin']);tree.append(dict(kind=r['kind'],**z))
 # Exact assignment from actual branch q[i] slots to actual current reset pins.
 targets=c['children']+c['banks'];slots=[(b,f'q[{i}]')for b in c['reset_nodes']if b['inst'].startswith('reset_branch')for i in range(16)];matrix=np.empty((len(targets),len(slots)));records={}
 for ti,t in enumerate(targets):
  for si,(b,pinname)in enumerate(slots):
   r=screen(b,pinname,t,'rst_n');records[ti,si]=r;matrix[ti,si]=1e9 if r is None else r['distance_um']+(1e6 if r['margin_ps']<15 else 0)
 rr,cc=linear_sum_assignment(matrix);assignments=[records[i,j]for i,j in zip(rr,cc)]
 clocks=[dict(instance=b['inst'],master=b['master'],orientation=b.get('orient','R0'),clock_pin='clk',actual_clock_xy_um=pin(b,'clk'),R_TT_ps=views[b['master']]['TT_boundary']['R_ps'],measured_parent_phase=None)for b in allb]
 face_abi=[]
 for n in ('n_a','n_b','n_y','t_out','tap'):
  b=by['face_'+n];o=old['face_'+n];face_abi.append(dict(parent_face=n,delta_xy_um=[round(b['x']-o['x'],6),round(b['y']-o['y'],6)],basis='Translate actual native parent pin window with unchanged face bank, preserving boundary-to-bank geometry; source/die contract must emit new pins',qualified=False))
 root=by['reset_root'];oldroot=old['reset_root'];oldglobal=reset['reset_contract']['root_global_pin_um'];newglobal=[oldglobal[0],round(oldglobal[1]+root['y']-oldroot['y'],6)]
 if a.prior_bundle:
  prior=json.loads(gzip.decompress(a.prior_bundle.read_bytes()));priorby={b['inst']:b for b in prior['bodies']}
  if any(by['face_'+n]!=priorby['face_'+n]for n in ('n_a','n_b','n_y','t_out','tap')) or by['reset_root']!=priorby['reset_root']:raise ValueError('Changed face/root pose requires explicit new parent ABI; cannot inherit')
  face_abi=prior['parent_face_ABI_changes'];newglobal=prior['reset']['global_parent_pin']['proposed_xy_um'];oldglobal=prior['reset']['global_parent_pin']['before_xy_um']
 out=dict(schema='opentallas.qwen.compressed-tile-source-bundle.v1',candidate_sha256=hashlib.sha256(a.candidate.read_bytes()).hexdigest(),source_inventory_sha256=hashlib.sha256(a.inventory.read_bytes()).hexdigest(),outline_um=c['outline_um'],bodies=allb,actual_views=views,source_file_sha256=hashes,clock_roots=clocks,data_bank_clock_index=[dict(index=i,instance=b['inst'],port=f'ck_bank[{i}]',actual_clock_xy_um=pin(b,'clk'))for i,b in enumerate(c['banks'])],residual_core_root=dict(home=None,clock_pin=None,synthesized_state_census_required=True),parent_face_ABI_changes=face_abi,reset=dict(source_topology=tree,target_assignment=assignments,target_count=len(targets),branch_slots=len(slots),all_tree_margins_ge15=all(r['margin_ps']>=15 for r in tree),all_target_margins_ge15=all(r is not None and r['margin_ps']>=15 for r in assignments),global_parent_pin=dict(before_xy_um=oldglobal,proposed_xy_um=newglobal,basis='Translate actual source reset parent pin with root displacement; preserve source-to-root geometry and original input contract',qualified=False),excluded_residual_core_target=dict(home=None,reason='Original220,720 placeholder is not actual physical source; preserve unresolved')),fixed_capture_map=d['fixed_capture_map'],existing_staged_cycle_ledger=d['cycle_ledger'],no_additional_pipeline_edges_beyond_staged_ledger=True,qualification=False,remaining=['Unmatched original payload endpoints and real control/combinational source','Source implementation equivalence/mutants including all reset/valid/metadata ages','Residual core state census and actual home','All parent clocks phi-R and actual routing/pin escape/TT/FF/DRC','Whole-die actual DVM/SU/IO/KV placement and reticle geometry'])
 a.out.write_bytes(gzip.compress(json.dumps(out,separators=(',',':')).encode(),mtime=0));print(json.dumps(dict(bodies=len(allb),clocks=len(clocks),reset_tree_min_margin_ps=min(r['margin_ps']for r in tree),reset_target_min_margin_ps=min(r['margin_ps']for r in assignments if r is not None),reset_target_fails=sum(r is None or r['margin_ps']<15 for r in assignments),source_bundle=str(a.out))))
if __name__=='__main__':main()
