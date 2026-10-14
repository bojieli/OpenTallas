#!/usr/bin/env python3
"""All-bit P2 candidate capacity for the other4010 lanes at proposed XPR14.
Real pin TTdeep210, FFH100 and SSzero necessary screens; no route/ABI adoption.
"""
import collections,gzip,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'results/arch/qwen_tp8_1012'
def main():
 summary=json.loads((A/'vm_band_boundary_packet_codex.json').read_text());p=json.load(gzip.open(ROOT/summary['packet']['path'],'rt'));j=json.loads((A/'vm_band_joint_staging_codex.json').read_text());joint=next(a for a in j['alternatives']if a['all688_bits_necessary_screens_pass']);hot={e['lane']for st in joint['stages']for e in st['bits']};geom=json.loads((A/'vm_band_joint_geometry_codex.json').read_text());control=json.loads((A/'vm_band_station_joint_candidate_codex.json').read_text());reserved={(c['candidate_destination']['bay'],c['candidate_destination']['slot'])for c in geom['candidate_children']if 'candidate_destination'in c};pool=[s for s in summary['spare_slots']if(s['bay'],s['slot'])not in reserved];controlslots={(s['slot']['bay'],s['slot']['slot'])for s in control['stations']};g=collections.defaultdict(list)
 for e in p['boundary_edges']:
  if e['lane']not in hot:g[e['lane']].append(e)
 names=sorted(g);rows=[sorted(g[n],key=lambda e:e['bit'])for n in names];assert len(rows)==4010 and all(len(r)==8 for r in rows)
 moves={(m['bay'],m['logical_slot']):next(c for c in geom['candidate_children']if c.get('bay')==m['bay']and c['slot']==m['logical_slot'])for m in j['prerequisite_whole_tile_relocations']};comp=json.loads((A/'vm_band_composition_codex.json').read_text());x0,y0=comp['origin_um'];old={(c['bay'],c['slot']):c for c in comp['children']if 'bay'in c}
 aa=np.array([[e['launch_xy_um']for e in r]for r in rows]);bb=np.array([[e['capture_xy_um']for e in r]for r in rows])
 for li,row in enumerate(rows):
  for bi,e in enumerate(row):
   st=e['capture_stage'];k=st['bay'],st['slot']
   if k in moves:bb[li,bi]+=np.array(moves[k]['at'])-np.array(old[k]['at'])
 def arc(role,corner,field):return np.array([[e['corner_budgets'][corner][role][field]for e in r]for r in rows])[:,None,:]
 lo=arc('launch','tt','o_ps');cs=arc('capture','tt','s_ps');lsl=arc('launch','ss','o_ps');css=arc('capture','ss','s_ps');lf=arc('launch','ff','l_ps');ch=arc('capture','ff','h_ps')
 dp=p['P2_actual_pins']['d'];qp=p['P2_actual_pins']['q'];dp_xy=np.array([z['xy_um']for z in dp]).reshape(60,8,2);qp_xy=np.array([z['xy_um']for z in qp]).reshape(60,8,2)
 def par(z,co,f):return np.array([x['corners'][co][f]for x in z]).reshape(1,60,8)
 ds=par(dp,'tt','s_ps');qo=par(qp,'tt','o_ps');dss=par(dp,'ss','s_ps');qos=par(qp,'ss','o_ps');dh=par(dp,'ff','h_ps');ql=par(qp,'ff','l_ps');choices=[[]for r in rows]
 for si,slot in enumerate(pool):
  origin=np.array(slot['at']);D=dp_xy+origin;Q=qp_xy+origin
  # At most256*60*8 distances per batch; bounded memory and exact allbit scans.
  count=0
  for start in range(0,len(rows),256):
   end=min(start+256,len(rows));l1=np.abs(aa[start:end,None,:,:]-D[None,:,:,:]).sum(axis=3);l2=np.abs(bb[start:end,None,:,:]-Q[None,:,:,:]).sum(axis=3)
   ok=(l1<=500)&(l2<=500)&(623.3333333333-lo[start:end]-ds-.76*l1>0)&(623.3333333333-qo-cs[start:end]-.76*l2>0)&(623.3333333333-lsl[start:end]-dss>0)&(623.3333333333-qos-css[start:end]>0)&(lf[start:end]-dh+.112*l1-100>0)&(ql-ch[start:end]+.112*l2-100>0)
   li,chunks=np.where(ok.all(axis=2))
   for lii,chh in zip(li.tolist(),chunks.tolist()):choices[start+lii].append(si*60+chh);count+=1
  print('slot',si+1,'of',len(pool),'candidate_pairs',count,flush=True)
 scenarios=[]
 for reservecontrols in (False,True):
  permitted={i for i,s in enumerate(pool)if not reservecontrols or(s['bay'],s['slot'])not in controlslots};filtered=[[v for v in c if v//60 in permitted]for c in choices];owner={};matched={}
  def augment(li,seen):
   for ch in filtered[li]:
    if ch in seen:continue
    seen.add(ch)
    if ch not in owner or augment(owner[ch],seen):owner[ch]=li;matched[li]=ch;return True
   return False
  unmatched=[]
  for li in sorted(range(len(rows)),key=lambda i:len(filtered[i])):
   if not augment(li,set()):unmatched.append(li)
  mapping=[dict(lane=names[li],slot=pool[ci//60],P2_bit0=8*(ci%60))for li,ci in matched.items()]
  scenarios.append(dict(reserved_control_station_slots=reservecontrols,available_slots=len(permitted),P2_capacity_bits=len(permitted)*480,matched_lanes=len(matched),unmatched_lanes=[names[i]for i in unmatched],no_single_P2_candidate_lanes=[names[i]for i,c in enumerate(filtered)if not c],used_whole_slots=len({ci//60 for ci in matched.values()}),partial_candidate_mapping=mapping))
 out=dict(schema='opentallas.qwen.vm-band-XPR14-other-lanes-candidate.v1',qualification=False,status='NECESSARY_PIN_MATCH_SCREEN_ONLY',hot_lanes=len(hot),remaining_lanes=len(rows),remaining_bits=8*len(rows),source_packet_sha256=summary['packet']['sha256'],
  proposed_XPR=14,setup_reserve_ps=210,SS='zero-wire only',FF='H100 with idealwirecredit; routed holdpending',scenarios=scenarios,
  pending=['A fullmatched scenario would still need physicalgeometry/cuts, localME and loader/loadstep equalization, allband input/internalpairrepair and realrouted sourceview.','No phase/epoch ABI adoption or originalpricechange.','Unmatched/no-candidate lanes need jointregional staging orchanged physicalcontract; do not waive truepairreach.'])
 (A/'vm_band_equalization_candidate_codex.json').write_text(json.dumps(out,indent=1)+'\n')
 print([{k:v for k,v in s.items()if k not in ('partial_candidate_mapping','unmatched_lanes','no_single_P2_candidate_lanes')}for s in scenarios])
if __name__=='__main__':main()
