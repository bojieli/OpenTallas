#!/usr/bin/env python3
import datetime, hashlib, json, os
from pathlib import Path
j = Path('/srv/opentallas-scratch2/jobs/kant-code-pair-reverse-constant-ties-20261005-r3')
w = j / 'route'
rec = dict(owner='Kant', variant='reverse-bank retained CTS with standard constant ties',
           terminal_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           route_exit=int(os.environ['KANT_ROUTE_RC']), corner_collection_exit=os.environ['KANT_CORNER_RC'],
           predecessor_failure_preserved='main f1364a286fd08ea25ca2fc271de6309fbd190841',
           synthesis_repeated=False, floorplan_repeated=False, cts_repeated=False,
           geometry_rtl_sdc_changed=False, adopted=False, clock_policy='CORE833.333ps SS60ps FF25ps')
rec['tie_successor'] = json.loads((w/'tie_successor.json').read_text())
rec['tie_cost_tsv'] = (w/'tie_cost.tsv').read_text() if (w/'tie_cost.tsv').exists() else None
logs = sorted((w/'logs').rglob('*.log'))
rec['errors'] = [{'file':str(p.relative_to(j)), 'line':s} for p in logs for s in p.read_text(errors='replace').splitlines() if '[ERROR' in s or 'Error ' in s]
if (j/'corner_sta.json').exists(): rec['corner_sta'] = json.loads((j/'corner_sta.json').read_text())
if (w/'capture_locality.json').exists(): rec['capture_locality'] = json.loads((w/'capture_locality.json').read_text())
rec['closes_signoff'] = rec.get('corner_sta',{}).get('closes_signoff',False)
loc = rec.get('capture_locality',{})
rec['passes_capture_locality'] = loc.get('all_capture_bits_present_in_bank_fence',False) and not loc.get('source_pin_distance_lower_bound_exceeds_budget',[1])
rec['verdict'] = ('PASS_MEASURED_CONTEXT_ONLY' if rec['route_exit']==0 and rec['corner_collection_exit']=='0' and rec['closes_signoff'] and rec['passes_capture_locality'] else 'FAILED_ROUTE' if rec['route_exit'] else 'FAILED_SIGNOFF_OR_LOCALITY')
# Whole macro/model timing remains distinct from macro SPICE and full parent closure.
rec['scope'] = '20 actual macro abstracts + standard cells + extracted SS/FF and2880 capture pins; not macro SPICE or whole HBM fit/adoption.'
(j/'outcome.json').write_text(json.dumps(rec,indent=2)+'\n')
art = {}
for p in sorted((w/'results').rglob('*')):
 if p.is_file() and (p.name.startswith('4_cts') or p.name.startswith('5_') or p.name.startswith('6_')):
  h=hashlib.sha256()
  with p.open('rb') as f:
   for data in iter(lambda:f.read(4*1024*1024),b''): h.update(data)
  art[str(p.relative_to(j))] = dict(bytes=p.stat().st_size,sha256=h.hexdigest())
(j/'retained_artifacts.json').write_text(json.dumps(art,indent=2)+'\n')
