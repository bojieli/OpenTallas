import gzip,json,collections,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
G=json.load(gzip.open(P/'historical_exterior/per_net_geometry.json.gz','rt'));V=json.load(open(P/'historical_exterior/verdict.json'))
counts=collections.Counter();rows=[];total_vias=0
RC={'M2':(.0297127,.174942),'M3':(.031287,.155554),'M4':(.0180365,.178475),'M5':(.0189935,.164264)}
def union(intervals):
 end=None;length=0
 for a,b in sorted(intervals):
  if end is None or a>end:length+=b-a;end=b
  elif b>end:length+=b-end;end=b
 return length/1000
for g in G:
 for z in g['leads']:z.setdefault('vertical_layer','M3')
 leads={z['point_index']:z for z in g['leads']};paths=[]
 total_vias+=g['base_via_count']
 for z in leads.values():counts['leads_'+z['vertical_layer']]+=1
 root=leads.get(0)
 metal=collections.defaultdict(list)
 metal[g['H_layer'],'H',g['H_y_nm']].append(g['H_x_nm'])
 for z in leads.values():
  metal[z['vertical_layer'],'V',z['M3_x_nm']].append(z['vertical_nm'])
  px,py=z['native_contact_nm'];metal[z['contact_jog_layer'],'H',py].append(sorted([px,z['M3_x_nm']]))
 layerlength=collections.Counter()
 for (layer,orient,coord),intervals in metal.items():layerlength[layer]+=union(intervals)
 unioncap=sum(RC[l][1]*v for l,v in layerlength.items());unioncaps={}
 for co,c in g['corner_cap'].items():
  value=c['native_plus_external_fF']+unioncap;limit=c['native_max_fF'];excess=limit is not None and value>limit
  if excess:counts['union_wire_cap_excess_'+co]+=1
  unioncaps[co]={'native_plus_external_fF':c['native_plus_external_fF'],'union_wire_fF':unioncap,'total_excluding_UNKNOWN_via_fringe_fF':value,'native_max_fF':limit,'cap_excess':excess}

 for i,z in leads.items():
  if i==0:continue
  if root is None:paths.append(None);continue
  rpx,rpy=root['native_contact_nm'];px,py=z['native_contact_nm'];rx=root['M3_x_nm'];x=z['M3_x_nm'];hy=g['H_y_nm']
  paths.append((abs(rpx-rx)+abs(rpy-hy)+abs(rx-x)+abs(py-hy)+abs(px-x))/1000)
 complete=g['native_contacts']==g['assigned_contacts'] and not g['construction_conflict']
 counts['nets_complete' if complete else 'nets_incomplete']+=1
 known=[z for z in paths if z is not None]
 maxpath=max(known,default=0) if complete else None
 if maxpath is not None and maxpath>405:counts['complete_net_path_exceeds405']+=1
 row=dict(net_index=g['net_index'],driver=g['driver'],all_contacts_assigned=g['native_contacts']==g['assigned_contacts'],complete_geometry=complete,root_to_contact_paths_um=paths,max_complete_root_path_um=maxpath,native_base_via_count=g['base_via_count'],new_native_via_fringing_cap='UNKNOWN_HOLD',native_max_caps=g['corner_cap'],union_wire_cap=unioncaps,union_wire_length_um=dict(layerlength))
 rows.append(row)
summary=dict(status='FAIL' if V['status']=='FAIL' or any(V['counts'].get('cap_violation_'+c,0) for c in ['TT','FF']) else 'GEOMETRY_ONLY_UNQUALIFIED',construction_verdict=V['status'],counts=dict(counts),native_base_vias=total_vias,native_via_count_scope='Per-contact transition ledger only, NOT unique implemented vias; boundary M4/M5 jog stacks and exact shared cuts remain HOLD',wire_cap_scope='Same-net collinear H/local-jog and M3/M5 segments UNIONED before native-wire cap; old per-contact summed cap values preserved but superseded as geometry capacitance',max_complete_root_path_um=max((r['max_complete_root_path_um'] for r in rows if r['max_complete_root_path_um'] is not None),default=None),missing_native_contact_records=V['counts']['contacts_total']-V['counts']['contacts_assigned'],geometry_sha256=hashlib.sha256((P/'historical_exterior/per_net_geometry.json.gz').read_bytes()).hexdigest(),all_via_fringe_waveform_setup_hold_clock_PG='HOLD',new_drive_buffers=0)
(P/'HISTORICAL_UNION_SUMMARY.json').write_text(json.dumps(summary,indent=2))
with gzip.open(P/'HISTORICAL_UNION_PATHS.json.gz','wt') as f:json.dump(rows,f)
print(json.dumps(summary,indent=2))
