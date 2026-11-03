"""Prepare disabled +12-live/fresh-master metadata; accepts no native state alias."""
from pathlib import Path
import argparse,copy,gzip,json,math
ap=argparse.ArgumentParser();ap.add_argument('--intent',type=Path,required=True);ap.add_argument('--clock',type=Path,required=True);ap.add_argument('--diagnosis',type=Path,required=True);ap.add_argument('--source-aliases',type=Path,required=True);ap.add_argument('--transition',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
def read(p):
 with (gzip.open(p,'rt') if str(p).endswith('.gz') else open(p)) as f:return json.load(f)
def write(p,x):
 data=(json.dumps(x,separators=(',',':'))+'\n').encode()
 if str(p).endswith('.gz'):
  with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(data)
 else:p.write_bytes(data)
intent=read(a.intent);clock=read(a.clock);d=read(a.diagnosis);aliases=read(a.source_aliases);trans=read(a.transition);a.out.mkdir(parents=True,exist_ok=True)
dead='u_bound.u_cland_origin/g_on.g_region[3].pd'
if aliases['missing_dead_source']!=[dead] or d['actual_new_ff']!=38243:raise ValueError('Source live census changed')
by={r['name']:r for r in d['fresh_master_changes']};source={r['model_name']:r['actual_candidates'] for r in aliases['rows']};proposed=trans['proposed_correspondence'];targets=[];rowchoices=[]
for old in intent['targets']:
 t=copy.deepcopy(old);name=t['model_name']
 if name==dead:continue
 if t['source_identity']:
  if len(source[name])!=1:raise ValueError('Ambiguous actual source phase name')
  t['native_name_candidate']=source[name][0]
 else:t['native_name_candidate']=proposed.get(name,name)
 if name in by:
  c=by[name];t.update(master=c['fresh_master'],width_um=c['fresh_width_um'],height_um=c['fresh_height_um'])
  t['old_place_master_reused']=False
  # Smaller fresh cells fit inside old footprints. Odd site-width differences
  # need a half-site center choice, coupled to all reach/clock constraints later.
  x,y=t['xy'];ll=x-t['width_um']/2
  if abs(ll/.054-round(ll/.054))>1e-5:
   dx=.027;t['xy_candidates']=[[x-dx,y],[x+dx,y]];rowchoices.append(name)
  t['placement']='HELD_FRESH_MASTER_ROW_REPRICE'
 t['native_name_candidate_accepted']=False;targets.append(t)
if len(targets)!=38243 or len({t['native_name_candidate'] for t in targets})!=38243:raise ValueError('Proposed fresh census is not bijective38243')
intent.update(schema='opentallas.tt_full_ff_fresh_phase_PREP.v1',enabled=False,status='HELD_NATIVE_CORRESPONDENCE_AND_FRESH_ROWS',targets=targets,target_count=len(targets),declared_net_ff_added=13,actual_mapped_net_ff_added=12,net_ff_added=12,source_slots_declared=16,source_slots_live=15,removed_unconsumed_source=dead,fresh_master_changes=len(by),fresh_half_site_choices=len(rowchoices),native_aliases_accepted=False,row_old87_terminal_required=True,geometry_all_pair_reaudit_required=True,tree_or_placement_applied=False)
# Preserve every existing port, root, edge and assignment; remove just deadPD3.
removed=[r for r in clock['assignments'] if r['name']==dead]
if len(removed)!=1 or removed[0]['parent_tap']!='clk_t52':raise ValueError('Clock source phase differs from exact observed deadPD3')
clock['assignments']=[r for r in clock['assignments'] if r['name']!=dead];clock['loads']['clk_t52']-=1;clock['main_sinks']-=1;clock['added_main_clock_ff']=12
bytarget={t['model_name']:t for t in targets}
for r in clock['assignments']:
 if r['name'] in bytarget:
  t=bytarget[r['name']];r['xy']=t['xy'];r['native_name_candidate']=t['native_name_candidate'];r['native_name_candidate_accepted']=False
  if 'xy_candidates' in t:r['xy_candidates']=t['xy_candidates']
  r['reach_um']='PENDING_FRESH_ROW_REPRICE'
clock.update(status='HELD_FRESH_MASTER_AND_NATIVE_PHASE_JOIN',enabled=False,declared_added_main_clock_ff=13,removed_dead_source_clock_endpoint=removed[0],native_aliases_accepted=False,physical_release=False,row_reprice_clock_reach_check_required=True)
write(a.out/'full_ff_intent_FRESH_PHASE_HELD.json.gz',intent);write(a.out/'clock_FRESH_PHASE_HELD.json.gz',clock)
report=dict(status='DISABLED_SOURCE_PHASE_PREP',target_count=38243,native_name_candidates=38243,native_correspondence_accepted=False,anonymous_candidates=23,source_declared_added_ff=13,source_actual_added_ff=12,source_declared_extra_reset_consumers=9,source_actual_extra_reset_consumers=8,live_new_source_sites=15,declared_source_sites=16,fresh_master_changes=244,fresh_half_site_choices=len(rowchoices),fresh_half_site_names=rowchoices,main_clock_sinks=clock['main_sinks'],other_clock_sinks=clock['nonmain_sinks_retained'],clock_ports=len(clock['clock_ports']),clock_period_ps=833,macro_plan_change='same reviewed gm0+8.64um only',cycles_added=0,required=['23-state source/control/BASE relation is not accepted by these candidate labels','active87-cell row terminal; integrate its actual complete homes without changing running inputs','fresh master207 half-site choices in complete DATA/reset/macro/clock/row collision audit','all63 native clock phase/name/port joins on actual fresh source','paired current parent plan/global reset/sidecar/G0C0new/strictbind0/global source receipt and actual LOOK before physical'],physical_release=False,full_lec_credit=False)
write(a.out/'report.json',report);print('FRESH_PHASE_DISABLED_PREP',38243,'FF',len(rowchoices),'half-site choices; all holds retained')
