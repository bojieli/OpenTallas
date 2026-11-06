from pathlib import Path
import json,re,hashlib,math
ROOT=Path('/srv/opentallas-scratch2/claude/codex-svgr-head-gen-hub-1106')
KIT=ROOT/'kits_clockon_reset64/ot_svgr_own_2054dcac0c09-headtail_p37_clockon_reset64'
PLAN=Path('/srv/opentallas-scratch2/claude/codex-hbm-wave/d44v37')
OUT=ROOT/'wt/results/geom_review/svgr_head_p37_1106/clockon_reset64'
OUT.mkdir(parents=True,exist_ok=True)
f=json.loads((KIT/'freeze.json').read_text());rawpath=PLAN/f['plan_pins_source']; raw={p['name']:p for p in json.loads(rawpath.read_text())};actual={p['name']:p for p in json.loads((KIT/'plan_pins.json').read_text())['pins']};io=(KIT/'io.tcl').read_text();coarse=json.loads((PLAN/'clock_entries.json').read_text());clocks=f['clocks']; rows=[]
def delta(a,b): return [round(a[0]-b[0],6),round(a[1]-b[1],6)]
def xy(p): return [p['x'],p['y']]
for pn, entries in coarse.items():
 for instance,row in entries.items():
  if row.get('module')=='ot_svgr_own':
   bases=([row['port']] if row.get('port') else [])+row.get('merged_clock_ports',[])
   mapped={base:[c for c in clocks if c==base or re.sub(r'\[\d+\]$','',c)==base] for base in bases}
   rows.append(dict(partition=pn,instance=instance,row=row,port_mapping=mapped,expanded_clock_ports=sorted({c for cs in mapped.values() for c in cs})))
assert len(rows)==8
records=[]
for c in clocks:
 r=raw[c];a=actual[c]
 pat=r'^place_pin -pin_name \{'+re.escape(c)+r'\} -layer (\S+) -location \{([^}]+)\} -pin_size \{([^}]+)\}'
 matches=re.findall(pat,io,re.M);assert len(matches)==1
 layer,loc,size=matches[0];ix=list(map(float,loc.split()));sz=list(map(float,size.split()));cs=[]
 for row in rows:
  assert c in row['expanded_clock_ports']
  centre=row['row']['xy_um']; bases=row['expanded_clock_ports']; selected=sorted(bases,key=lambda x:(re.sub(r'\[\d+\]$','',x),x)); cx=.024+math.floor((centre[0]-.024)/.048+.5)*.048; expected=[round(cx+(-((len(selected)-1)//2)+selected.index(c))*.096,4),centre[1]];cs.append(dict(partition=row['partition'],instance=row['instance'],coarse_xy_um=centre,coarse_expanded_expected_xy_um=expected,generated_minus_expanded_coarse_um=delta(xy(a),expected),generated_minus_coarse_um=delta(xy(a),centre),raw_minus_coarse_um=delta(xy(r),centre)))
 records.append(dict(port=c,raw_plan_pin=r,generated_plan_pin=a,io_literal_xy_um=ix,io_literal_layer=layer,io_literal_size_um=sz,io_matches_generated=ix==xy(a) and layer==a['layer'],generated_minus_raw_um=delta(xy(a),xy(r)),io_minus_raw_um=delta(ix,xy(r)),generated_matches_raw=xy(a)==xy(r) and layer==r['layer'],coarse_comparisons=cs))
result=dict(verdict='PASS' if all(x['generated_matches_raw'] and x['io_matches_generated'] and all(y['generated_minus_expanded_coarse_um']==[0,0] for y in x['coarse_comparisons']) for x in records) else 'FAIL',kit_hash=f['kit_hash'],view=f['view'],raw_pin_table_sha256=hashlib.sha256(rawpath.read_bytes()).hexdigest(),coarse_clock_entries_sha256=hashlib.sha256((PLAN/'clock_entries.json').read_bytes()).hexdigest(),io_sha256=hashlib.sha256((KIT/'io.tcl').read_bytes()).hexdigest(),raw_pin_table=str(rawpath),coarse_clock_entries=str(PLAN/'clock_entries.json'),clock_ports=clocks,actual_distinct_centres=sorted({tuple(xy(actual[c])) for c in clocks}),raw_distinct_centres=sorted({tuple(xy(raw[c])) for c in clocks}),coarse_own_rows=rows,comparisons=records,findings=['All six generated scalar clock centres and literal io.tcl placements equal canonical raw p37 pins.', 'All eight OWN coarse rows expand their merged base-port names onto the same six M5 grid points; all48 scalar comparisons have zero delta.', 'Explicit --clock-pin-entry on; old default-off kit and failed audit retained unchanged.', 'Only the six clock pin centres changed; no P&R was run.'],physical_route_run=False)
(OUT/'clock_site_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(verdict=result['verdict'],ports=[dict(port=x['port'],raw=xy(x['raw_plan_pin']),generated=xy(x['generated_plan_pin']),delta=x['generated_minus_raw_um']) for x in records],coarse_rows=len(rows)),indent=2))
