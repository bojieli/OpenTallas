#!/usr/bin/env python3
"""Full band child geometry and all-corner necessary checks for two relocations."""
import collections,gzip,json,hashlib
from pathlib import Path
from vm_bay_cluster import VIEW
from vm_band_pair import timing
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'results/arch/qwen_tp8_1012'
def main():
 comp=json.loads((A/'vm_band_composition_codex.json').read_text());jf=A/'vm_band_joint_staging_codex.json';joint=json.loads(jf.read_text());chosen=next(a for a in joint['alternatives']if a['all688_bits_necessary_screens_pass']);rp=A/'vm_band_paths_closed_station_candidate_codex.json';r=json.loads(rp.read_text());edges=json.load(gzip.open(ROOT/r['all_bit_details']['path'],'rt'))['edges'];x0,y0=comp['origin_um'];W,H=comp['outline_um'];pool=json.loads((A/'vm_band_boundary_packet_codex.json').read_text())['spare_slots'];children=comp['children'];moves={};new=[]
 for move in joint['prerequisite_whole_tile_relocations']:
  ch=next(c for c in children if c.get('bay')==move['bay']and c['slot']==move['logical_slot']);dest=next(s for s in pool if s['bay']==move['to_bay']and s['slot']==move['physical_slot']);nx,ny=dest['at'];dx=nx-x0-ch['at'][0];dy=ny-y0-ch['at'][1];moves[move['bay'],move['logical_slot']]=(dx,dy);ch['at']=[nx-x0,ny-y0];ch['candidate_destination']=dest
 for i,stage in enumerate(chosen['stages']):
  x,y=stage['band_slot']['at_um'];ch=dict(inst=f'candidate_band_exit{i+1}',view=VIEW[stage['relay_kind']],at=[x-x0,y-y0],outline_um=[17.28,97.2]);children.append(ch);new.append(ch)
 def side(view,pin,corner):
  m,refs=timing(view,corner);z=m[pin];ref=refs[z['clk'][0]]
  return dict(o=None if z['out']is None else z['out']+ref['bmax']-ref['rise'],s=None if z['inp']is None else z['inp']+ref['rise']-ref['bmin'],l=None if z['lmin']is None else z['lmin']+ref['bmin']-ref['rise'],h=None if z['hold']is None else z['hold']+ref['rise']-ref['bmax'])
 affected=[];cmap={(c['bay'],c['slot']):c for c in children if 'bay'in c}
 for e in edges:
  la=e.get('launch',{});ca=e.get('capture',{});lk=(la.get('bay'),la.get('slot'));ck=(ca.get('bay'),ca.get('slot'))
  if lk not in moves and ck not in moves:continue
  ax,ay=e['A'];bx,by=e['B']
  if lk in moves:dx,dy=moves[lk];ax+=dx;ay+=dy
  if ck in moves:dx,dy=moves[ck];bx+=dx;by+=dy
  L=abs(ax-bx)+abs(ay-by);lp=f'q[{la["bit0"]+la.get("bit_permutation",list(range(8)))[e["bit"]]}]';lv=VIEW[la['kind']]
  if e['kind']=='closed_column_input':cv='physical/ref_tile/qfd_vm_xcol_roots/views/ot_qfd_vm_xcol_roots';cp=e['capture_pin']
  else:cv=cmap[ck]['view'];cp=f'd[{ca["bit0"]+ca.get("bit_permutation",list(range(8)))[e["bit"]]}]'
  tt_l=side(lv,lp,'tt');tt_c=side(cv,cp,'tt');ss_l=side(lv,lp,'ss');ss_c=side(cv,cp,'ss');ff_l=side(lv,lp,'ff');ff_c=side(cv,cp,'ff')
  tt=833.3333333333-210-tt_l['o']-tt_c['s']-.76*L;ss=833.3333333333-210-ss_l['o']-ss_c['s'];hold=ff_l['l']-ff_c['h']+.112*L-100
  affected.append(dict(kind=e['kind'],lane=e['lane'],bit=e['bit'],A=[ax,ay],B=[bx,by],length_um=L,TT_deep210_setup_ps=tt,SS_zero_wire_setup_ps=ss,FF_H100_ideal_wire_ps=hold,launch_view=lv,launch_pin=lp,capture_view=cv,capture_pin=cp))
 failures=[];minchannels=9999;checks=0
 for i,c in enumerate(children):
  for d in children[i+1:]:
   checks+=1;dx=max(c['at'][0],d['at'][0])-min(c['at'][0]+c['outline_um'][0],d['at'][0]+d['outline_um'][0]);dy=max(c['at'][1],d['at'][1])-min(c['at'][1]+c['outline_um'][1],d['at'][1]+d['outline_um'][1]);gap=max(dx,dy);minchannels=min(minchannels,gap)
   if gap<2.16-1e-6:failures.append(dict(a=c['inst'],b=d['inst'],gap_um=gap))
 outside=[c['inst']for c in children if min(c['at'])<0 or c['at'][0]+c['outline_um'][0]>W+1e-6 or c['at'][1]+c['outline_um'][1]>H+1e-6]
 out=dict(schema='opentallas.qwen.vm-band-joint-geometry-necessary-gate.v1',qualification=False,status='NECESSARY_GEOMETRY_AND_RELOCATION_PASS'if not failures and not outside and all(min(e['TT_deep210_setup_ps'],e['SS_zero_wire_setup_ps'],e['FF_H100_ideal_wire_ps'])>0 and e['length_um']<=500 for e in affected)else 'FAIL',
  selected_joint_alternative=chosen['assignment'],selected_relay_kinds=chosen['relay_kinds'],source_joint_sha256=hashlib.sha256(jf.read_bytes()).hexdigest(),
  candidate_children=children,preserved_original_children=302,added_band_tiles=2,all_child_pair_checks=checks,minimum_channel_um=minchannels,geometry_failures=failures,outside_children=outside,
  relocated_affected_edges=len(affected),relocated_corner_worst={key:min(e[key]for e in affected)for key in ('TT_deep210_setup_ps','SS_zero_wire_setup_ps','FF_H100_ideal_wire_ps')},relocated_edges=affected,
  scope='Two whole relocated existing tiles and two added bandrelays only; original302 plus2band; regional2newtiles checked byregionworker. All4096originalstages/indexorder unchanged. Added688paths separately jointstaging matched.',
  pending=['Uniform all4096 proposedXPR14 equalization, source/control/ME/load_step domain changes, actual SS wire and routed hold.','Actualrouted snapshotinputviews, completeclockentryclassifications, gatherstations/tagsABI/cut/fullnativeperformance.'])
 (A/'vm_band_joint_geometry_codex.json').write_text(json.dumps(out,indent=1)+'\n');print(out['status'],out['all_child_pair_checks'],out['minimum_channel_um'],out['relocated_affected_edges'],out['relocated_corner_worst'])
if __name__=='__main__':main()
