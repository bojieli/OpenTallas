#!/usr/bin/env python3
"""Source-pinned actual-ETM capture internal pair screen; no route or signoff.

Exact related_pin references only. Same-domain hops use their native period;
matching fixed-bank t/s leaves retain the compiled epoch-window constraints.
FF hold conservatively credits no unmeasured minimum die-wire delay.
"""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normalize_clock(p):return p[:-3] if p.endswith('[0]') else p

def rehome(data, changes):
 for n,at in changes.items():
  c=data['children'][n];c['at_um']=at
  for p in c['pins'].values():p['xy_um']=[round(at[i]+p['local_xy_um'][i],6) for i in (0,1)]
 for e in data['clock_entries']:e['xy_um']=data['children'][e['child']]['pins'][e['pin']]['xy_um']
 for p in data['die_ports'].values():
  for e in p['contacts']:e['xy_um']=data['children'][e['child']]['pins'][e['pin']]['xy_um']
 for p in data['internal_paths']:
  def xy(ep):
   n,pin=ep.rsplit('/',1);return data['children'][n]['pins'][pin]['xy_um']
  p['manhattan_um']=round(sum(abs(a-b) for a,b in zip(xy(p['driver']),xy(p['sink']))),6)
 data['candidate_home_changes_um']=changes
 data['scope']='Source-current structural rehome candidate; same17 LEFs/70leaves/86clocks, zero area/cycle cost, full-die qualification pending'

def geometry(data):
 outside=[];overlap=[];gaps=[]
 for n,a in data['children'].items():
  if any(a['at_um'][i]<0 or a['at_um'][i]+a['outline_um'][i]>data['outline_um'][i]+1e-6 for i in (0,1)):outside.append(n)
  for m,b in data['children'].items():
   if n>=m:continue
   gap=max(b['at_um'][0]-a['at_um'][0]-a['outline_um'][0],a['at_um'][0]-b['at_um'][0]-b['outline_um'][0],b['at_um'][1]-a['at_um'][1]-a['outline_um'][1],a['at_um'][1]-b['at_um'][1]-b['outline_um'][1])
   if gap < -1e-6:overlap.append([n,m])
   if gap<20-1e-6 and (n in data.get('candidate_home_changes_um',{}) or m in data.get('candidate_home_changes_um',{})):gaps.append({'a':n,'b':m,'gap_um':gap})
 return {'outside':outside,'overlaps':overlap,'moved_child_pairs_below20um_gap':gaps}

def run(root,packet,changes=None):
 sys.path.insert(0,str(root/'tools/hier_contract'))
 from pinreg_audit import parse_lib
 path=packet if packet.is_absolute() else root/packet
 data=json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
 if changes:rehome(data,changes)
 geom=geometry(data);assert not geom['outside'] and not geom['overlaps'],geom
 for rel,digest in data['source_sha256'].items():
  assert sha(root/rel)==digest,('source hash mismatch',rel)
 for v in data['views'].values():
  for rel,digest in v['sha256'].items():assert sha(root/rel)==digest,('view hash mismatch',rel)
 entries={(e['child'],e['pin']):e for e in data['clock_entries']}
 metrics={};view_clocks={};hashes={}
 for master,v in data['views'].items():
  view=root/v['view'];ins=json.loads((view/'insertion.json').read_text());cms=ins.get('clock_measurements',{})
  if not cms:
   # Legacy single-entry records name their literal SDC port in `clock`.
   # This is exact name matching, never spatial/nearest-root inference.
   literal=ins.get('lib_clock_pin') or ins.get('clock')
   expected={e['pin'] for e in data['clock_entries'] if data['children'][e['child']]['master']==master}
   assert literal and len(expected)==1 and normalize_clock(literal)==normalize_clock(next(iter(expected))),('missing exact clock measurement',master,literal,expected)
   cms={literal:ins}
  for co in ('tt','ff'):
   lib=parse_lib(view/(master+'_'+co+'.lib'));values={}
   for pin,p in lib['pins'].items():
    launch=defaultdict(list);capture=defaultdict(list);hold=defaultdict(list);earliest=defaultdict(list)
    for typ,rel,tables in p['arcs']:
     if typ not in ('rising_edge','falling_edge','setup_rising','setup_falling','hold_rising','hold_falling'):continue
     if typ in ('rising_edge','falling_edge'):
      a=[tables[k][0] for k in ('cell_rise','cell_fall') if tables.get(k)]
      if a:launch[rel].append(max(a));earliest[rel].append(min(a))
     else:
      a=[x for k in ('rise_constraint','fall_constraint') for x in tables.get(k,[])]
      if a:(capture if typ.startswith('setup') else hold)[rel].append(max(a))
    clocks=set(launch)|set(capture)|set(hold);out={}
    for clock in clocks:
     matches=[c for c in cms if normalize_clock(c)==normalize_clock(clock)]
     assert len(matches)==1,('literal related clock has no unique insertion reference',master,pin,clock,matches)
     cm=cms[matches[0]];assert normalize_clock(cm.get('lib_clock_pin') or cm['clock'])==normalize_clock(clock)
     boundary=cm[co]['boundary'];R=boundary['mean']
     out[clock]={'clock':clock,'R_ps':R,'R_source':'insertion.json exact literal clock boundary mean (per-entry record; legacy single-entry top record only when clock name matches exactly)','spread_ps':boundary['max']-boundary['min'],
                 'launch_ps':max(launch[clock])-R if launch[clock] else None,'earliest_launch_ps':min(earliest[clock])-R if earliest[clock] else None,
                 'setup_ps':max(capture[clock])+R if capture[clock] else None,'hold_ps':max(hold[clock])-R if hold[clock] else None}
    values[pin]=out
   metrics[(master,co)]=values
 def endpoint(path,co):
  n,pin=path.rsplit('/',1);master=data['children'][n]['master'];vs=metrics[(master,co)].get(pin,{})
  for clock,v in vs.items():
   exact=[e for (cn,cp),e in entries.items() if cn==n and normalize_clock(cp)==normalize_clock(clock)]
   assert len(exact)==1,('endpoint related clock has no literal parent clock contact',path,clock)
   v['domain']=exact[0]['domain'];v['parent_clock_pin']=exact[0]['parent_clock_pin']
  return n,master,vs
 pairs=[];unresolved=[];static=[]
 # The exact pinned source states these exclusions; neither is an inferred clock.
 cd=(root/'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_cd.sv').read_text()
 ctl=(root/'rtl/dsrom_sys/s81_ph/ot_s81ph_cap_tile.sv').read_text()
 assert "fs_q <= {f_st[13:2], 1'b0, f_st[0]}" in cd
 assert "s_now <= {g_busy, g_live, 1'b0, h_id, h_ph, cfault | proto_fault | g_fault, phase_drained, phase_idle, phase_live}" in ctl
 for path in data['internal_paths']:
  dn,dm,dtt=endpoint(path['driver'],'tt');sn,sm,stt=endpoint(path['sink'],'tt')
  _,_,dff=endpoint(path['driver'],'ff');_,_,sff=endpoint(path['sink'],'ff')
  variants=[]
  for dc,d in dtt.items():
   if d['launch_ps'] is None:continue
   for sc,s in stt.items():
    if s['setup_ps'] is None:continue
    assert dc in dff and sc in sff
    df,sf=dff[dc],sff[sc]
    if df['earliest_launch_ps'] is None or sf['hold_ps'] is None:continue
    same=d['domain']==s['domain']
    seam=(not same and dn.rsplit('.',1)[0]==sn.rsplit('.',1)[0] and ((re.search(r'_(?:x8x|x43)_t(?:_|$)',dm) and re.search(r'_(?:x8x|x43)_s(?:_|$)',sm)) or (re.search(r'_(?:x8x|x43)_s(?:_|$)',dm) and re.search(r'_(?:x8x|x43)_t(?:_|$)',sm))))
    cls='same_'+d['domain'] if same else 'scheduled_3to4_bank' if seam else 'UNSCHEDULED_CROSS_DOMAIN'
    if not same and not seam:raise ValueError(('cross-domain pair lacks matching compiled bank seam',path,dm,sm))
    skew=150.0 if (not same or d['R_ps']>300 or s['R_ps']>300) else 90.0
    window=(833.333 if d['domain']=='stream' else 1111.111) if same else 1388.889
    hold_window=0.0 if same else 1111.111
    length=path['manhattan_um'];setup_available=window-60.0-skew
    residual=d['launch_ps']+s['setup_ps'];setup_margin=setup_available-residual-0.76*length
    hold_gap=df['earliest_launch_ps']-sf['hold_ps'];hold_margin=hold_gap+hold_window-100.0
    variants.append({'class':cls,'direction':d['domain']+'_to_'+s['domain'],'launch_clock':dc,'capture_clock':sc,'launch_parent_clock':d['parent_clock_pin'],'capture_parent_clock':s['parent_clock_pin'],
     'launch_R_tt_ps':d['R_ps'],'capture_R_tt_ps':s['R_ps'],'launch_R_ff_ps':df['R_ps'],'capture_R_ff_ps':sf['R_ps'],
     'launch_tt_ps':d['launch_ps'],'capture_setup_tt_ps':s['setup_ps'],'earliest_launch_ff_ps':df['earliest_launch_ps'],'capture_hold_ff_ps':sf['hold_ps'],
     'setup_window_ps':window,'hold_window_ps':hold_window,'setup_skew_ps':skew,'setup_available_ps':setup_available,'pair_residual_tt_ps':residual,
     'pair_reach_um':(setup_available-residual)/0.76,'setup_margin_ps':setup_margin,'hold_zero_wire_margin_ps':hold_margin,'required_min_wire_delay_ps':max(0.0,-hold_margin)})
  if not variants:
   proof=None
   if path['driver']=='u_status.u_s/t_st[1]' and path['sink']=='u_cd/f_st[1]':proof={'kind':'source-proven unused sink','source':'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_cd.sv','proof':"PINREG=1 fs_q <= {f_st[13:2], 1'b0, f_st[0]}; f_st[1] discarded; ETM f_st[1] cap0/no setup/hold."}
   if path['driver']=='u_ctl/t_sn[61]' and path['sink']=='u_sn/i[61]':proof={'kind':'source-proven constant output','source':'rtl/dsrom_sys/s81_ph/ot_s81ph_cap_tile.sv','proof':"s_now <= {g_busy,g_live,1'b0,h_id[46:0],h_ph[9:0],fault,drained,idle,live}; t_sn[61]=0 both normal/reset; ETM t_sn[61] no launch arc."}
   if proof:static.append({'path':path,**proof});continue
   unresolved.append({'path':path,'launch_tt_clocks':list(dtt),'capture_tt_clocks':list(stt),'reason':'missing launch/setup/earliest/hold data arc'});continue
  worst_setup=min(variants,key=lambda q:q['setup_margin_ps']);worst_hold=min(variants,key=lambda q:q['hold_zero_wire_margin_ps'])
  pairs.append({**path,'source_master':dm,'sink_master':sm,'class':worst_setup['class'],'setup_margin_ps':worst_setup['setup_margin_ps'],'hold_zero_wire_margin_ps':worst_hold['hold_zero_wire_margin_ps'],
                'pair_reach_um':worst_setup['pair_reach_um'],'setup_fail':worst_setup['setup_margin_ps']<0,'hold_zero_wire_unproven':worst_hold['hold_zero_wire_margin_ps']<0,'required_min_wire_delay_ps':max(0.0,-worst_hold['hold_zero_wire_margin_ps']),'clock_arc_variants':variants})
 classes={}
 for cls in sorted({p['class'] for p in pairs}):
  ps=[p for p in pairs if p['class']==cls];groups=defaultdict(list)
  for p in ps:groups[(p['source_master'],p['sink_master'])].append(p)
  classes[cls]={'bit_joins':len(ps),'setup_fails':sum(p['setup_fail'] for p in ps),'hold_zero_wire_unproven':sum(p['hold_zero_wire_unproven'] for p in ps),
   'min_setup_margin_ps':min(p['setup_margin_ps'] for p in ps),'min_hold_zero_wire_margin_ps':min(p['hold_zero_wire_margin_ps'] for p in ps),
   'max_wire_um':max(p['manhattan_um'] for p in ps),'min_pair_reach_um':min(p['pair_reach_um'] for p in ps),
   'master_pairs':[{'source':a,'sink':b,'bits':len(g),'setup_fails':sum(p['setup_fail'] for p in g),'hold_zero_wire_unproven':sum(p['hold_zero_wire_unproven'] for p in g),
    'min_setup_margin_ps':min(p['setup_margin_ps'] for p in g),'min_hold_zero_wire_margin_ps':min(p['hold_zero_wire_margin_ps'] for p in g)} for (a,b),g in sorted(groups.items())]}
 failures=[p for p in pairs if p['setup_fail'] or p['hold_zero_wire_unproven']]
 report={'schema':'opentallas.s81.capture_internal_pair_preflight.v1','packet_sha256':sha(packet if packet.is_absolute() else root/packet),
  'source_sha256':data['source_sha256'],'views_sha256':{m:v['sha256'] for m,v in data['views'].items()},'tool_sha256':sha(Path(__file__)),'pin_parser_sha256':sha(root/'tools/hier_contract/pinreg_audit.py'),
  'scope':'Actual TT/FF ETM pin-pair preflight on candidate LEF contact homes; first/lightest-load ETM output samples, no routed RC/load/fanout/clock-delivery qualification.',
  'policy':{'setup_wire_ps_per_um':0.76,'setup_uncertainty_ps':60,'same_level_setup_skew_ps':90,'cross_level_or_domain_setup_skew_ps':150,'hold_requirement_ps':100,'hold_wire_credit_ps':0,
    'scheduled_setup_window_ps':1388.889,'scheduled_hold_window_ps':1111.111,'reset':'External rst/rsv source release, distribution and epoch alignment remain UNQUALIFIED; no reset source timing inferred.'},
  'counts':{'requested_bit_joins':len(data['internal_paths']),'timed_bit_joins':len(pairs),'unresolved_bit_joins':len(unresolved),'source_proven_static_joins':len(static),'setup_fails':sum(p['setup_fail'] for p in pairs),'hold_zero_wire_unproven':sum(p['hold_zero_wire_unproven'] for p in pairs)},
  'geometry':geom,'candidate_home_changes_um':data.get('candidate_home_changes_um',{}),'structural_cost':{'added_cycles':0,'added_area_um2':0,'added_instances':0,'added_clock_contacts':0,'moved_clock_contacts':sum(e['child'] in data.get('candidate_home_changes_um',{}) for e in data['clock_entries'])},'real_pin_defects':[m for m,v in data['views'].items() if not v['native_audit']['pass']],'static_exclusions':static,'classes':classes,'unresolved':unresolved,'worst_setup':sorted(pairs,key=lambda p:p['setup_margin_ps'])[:30],'worst_hold':sorted(pairs,key=lambda p:p['hold_zero_wire_margin_ps'])[:30],'failing_pairs':failures}
 return report,pairs,data

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--packet',type=Path,default=Path('physical/s81_die_pins/capture_split_1016/source_current_binding.json.gz'));p.add_argument('--out',type=Path,required=True);p.add_argument('--rehome-json',type=Path);a=p.parse_args()
 report,pairs,data=run(a.root,a.packet,json.loads(a.rehome_json.read_text()) if a.rehome_json else None);a.out.mkdir(parents=True,exist_ok=True);(a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(a.out/'all_pairs.json.gz').write_bytes(gzip.compress(json.dumps(pairs,separators=(',',':')).encode(),mtime=0));(a.out/'candidate_packet.json.gz').write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0)) if a.rehome_json else None;print(json.dumps({'counts':report['counts'],'classes':{k:{a:b for a,b in v.items() if a!='master_pairs'} for k,v in report['classes'].items()}}))
