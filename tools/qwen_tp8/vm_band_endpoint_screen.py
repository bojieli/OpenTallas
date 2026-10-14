#!/usr/bin/env python3
"""Full compensated launch220/capture190 necessary interface screen.
Native seam distances project to nearest required region/band face; X port
assignment and real RC remain pending. No double subtraction of clock R.
"""
import collections,gzip,json,hashlib
from pathlib import Path
from vm_band_pair import timing
from vm_bay_cluster import VIEW
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'results/arch/qwen_tp8_1012'
def main():
 pf=A/'vm_band_boundary_packet_codex.json';p=json.loads(pf.read_text());packet=json.load(gzip.open(ROOT/p['packet']['path'],'rt'));comp=json.loads((A/'vm_band_composition_codex.json').read_text());leaf=json.loads((A/'vm_leaf_plan_claude.json').read_text());x0,y0=comp['origin_um'];H=comp['outline_um'][1];seams=[]
 for e in packet['boundary_edges']:
  yy=y0 if e['region']<4 else y0+H;outdist=abs(e['launch_xy_um'][1]-yy);indist=abs(e['capture_xy_um'][1]-yy);o=e['corner_budgets']['tt']['launch']['o_ps'];s=e['corner_budgets']['tt']['capture']['s_ps']
  seams.append(dict(lane=e['lane'],bit=e['bit'],region=e['region'],launch=e['launch_stage'],capture=e['capture_stage'],required_face='Nregion/Sband'if e['region']<4 else'Sregion/Nband',nearest_face_y_um=yy,
   normalized_o_with_spread_ps=o,normalized_s_with_spread_ps=s,optimistic_leaf_to_face_um=outdist,optimistic_face_to_leaf_um=indist,
   zero_wire_launch_over220=o>220,zero_wire_capture_over190=s>190,launch220_TT_lower_bound_margin_ps=220-o-.76*outdist,capture190_TT_lower_bound_margin_ps=190-s-.76*indist,
   note='Nearestface Xprojection is optimistic, notassignedpin; actualfacewire/Xjog/OBS/RC can onlyaddcost'))
 r=json.loads((A/'vm_band_paths_closed_station_candidate_codex.json').read_text());detail=json.load(gzip.open(ROOT/r['all_bit_details']['path'],'rt'));inputs=[]
 for e in detail['edges']:
  if e['kind']!='closed_column_input':continue
  la=e['launch'];lv=VIEW[la['kind']];lp=f'q[{la["bit0"]+la.get("bit_permutation",list(range(8)))[e["bit"]]}]';cv='physical/ref_tile/qfd_vm_xcol_roots/views/ot_qfd_vm_xcol_roots';cp=e['capture_pin'];lm,lr=timing(lv);cm,cr=timing(cv);l=lm[lp];c=cm[cp];lref=lr[l['clk'][0]];cref=cr[c['clk'][0]];o=l['out']+lref['bmax']-lref['rise'];s=c['inp']+cref['rise']-cref['bmin']
  inputs.append(dict(lane=e['lane'],bit=e['bit'],launch_pin=lp,capture_pin=cp,launch_view=lv,capture_view=cv,length_um=e['length_um'],normalized_o_with_spread_ps=o,normalized_s_with_spread_ps=s,
   intrinsic_launch220_margin_ps=220-o,intrinsic_capture190_margin_ps=190-s,pair_TT_margin_ps=e['pair_slack_ps'],pair_deep210_margin_ps=e['deep_entry_slack_ps'],
   interpretation='Closedleaf intrinsic220/190 checks plusactualpair. Bandinternal wire is separate; no fictitiousface/pin or doublecharge applied. Actual hardenedbandendpointplanes pending.'))
 def stats(es,keys):return{key:dict(failed=sum(e[key]<0 for e in es),worst_ps=min(e[key]for e in es))for key in keys}
 df=A/'vm_band_endpoint_screen_codex.details.json.gz'
 with gzip.open(df,'wt')as f:json.dump(dict(native_region_to_band=seams,final_pad_to_pointroot=inputs),f,separators=(',',':'))
 out=dict(schema='opentallas.qwen.vm-band-full-endpoint-screen.v1',qualification=False,status='REJECTED_NATIVE_FULL_BOUNDARY_INTERFACE_NO_ROUTE',launch_limit_ps=220,capture_limit_ps=190,
  normalization='pinreg_audit metrics alreadyO-R/S+R; only measured boundaryspread adjustment added. Clockentrywire is compensated separately, not datawire.',
  native_seam_bits=len(seams),native_seam_stats=stats(seams,('launch220_TT_lower_bound_margin_ps','capture190_TT_lower_bound_margin_ps')),
  native_intrinsic=dict(launch_over220=sum(e['zero_wire_launch_over220']for e in seams),capture_over190=sum(e['zero_wire_capture_over190']for e in seams)),
  pointroot_input_bits=len(inputs),pointroot_stats=stats(inputs,('intrinsic_launch220_margin_ps','intrinsic_capture190_margin_ps','pair_TT_margin_ps','pair_deep210_margin_ps')),
  pointroot_source='eeb5c1dc5 heldpointviewdiagnostic; snapshotroutedviewpending',source_hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in (pf,A/'vm_band_paths_closed_station_candidate_codex.json')},
  detail=dict(path=str(df.relative_to(ROOT)),sha256=hashlib.sha256(df.read_bytes()).hexdigest()),
  candidate_rejection=dict(regional_first_stage_packet='b48c892d',rejection_source='4c14ae277 vm_joint_g1_station_endpoint_screen.json',intrinsic_bad_outputs=53,all688_Nface_launch220_fail=True,
   interpretation='ChosenW,E joint688screens/geometry remain necessarytests only; fullinterface rejection prevents freezing/adopting/rerouting.'),
  pending=['Actual source/bandassigned boundarypins andendpointbudgetplanes; closest-face projection onlynecessarylowerbound.','ENGINE-qualified shallow S/Nclosedviews orotherphysicallyjustified endpoints; no clockRdoublecredit.','Actual M8/M9/bufferingrecipe SS endpointRC/hold, fullclock/control/loader protocol, combinedcuts.'])
 (A/'vm_band_endpoint_screen_codex.json').write_text(json.dumps(out,indent=1)+'\n');print(out['native_seam_stats'],out['native_intrinsic'],out['pointroot_stats'])
if __name__=='__main__':main()
