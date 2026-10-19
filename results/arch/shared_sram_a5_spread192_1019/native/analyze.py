import json,re
from pathlib import Path
from collections import Counter
from graph import connected,overlap
P=Path(__file__).resolve().parent;results={}
for name in ['qwen','sc2','controls','missing_bridge','short_bridge']:
 p=P/'native'/name
 if not p.exists():p=P/name
 cases=json.loads((p/'coupon.json').read_text())['cases'];ledger=json.loads((p/'native_shape_ledger.json').read_text());out={}
 for ci,c in enumerate(cases):
  boxes=[]
  for n in p.glob(f'odb_net_{ci}_*.json'):
   d=json.loads(n.read_text());assert d['exact_box_multiset'];assert set(d['wire_type'])=={'ROUTED'};assert d['sig_type']=='SIGNAL'
   for k,(layer,r) in enumerate(d['actual_boxes']):boxes.append({'identity':n.stem+':'+str(k),'net':d['source_net'],'layer':layer,'rect_nm':r})
  vias=[]
  for v in ledger:
   if v['case']==ci and 'via' in v:
    vias.append({'identity':v['source_identity'],'net':v['source_net'],'boxes_nm':{b['layer']:b['rect_nm'] for b in v['native_boxes']}})
  con=connected(boxes,vias,c.get('ports',[]))
  shorts=[];sup=[b for b in boxes if b['net'] in ['VDD','VSS'] and b['layer'].startswith('M')]
  for j,a in enumerate(sup):
   for b in sup[j+1:]:
    if a['net']!=b['net'] and a['layer']==b['layer'] and overlap(a['rect_nm'],b['rect_nm']):shorts.append([a['identity'],b['identity'],a['layer']])
  out[c['name']]={'actual_boxes':len(boxes),'complete_native_vias':len(vias),'connectivity':con,'actual_crossnet_overlaps':shorts,'whole_graph_connected':all(z['components']==1 for z in con.values()) and not shorts}
 globalreport=(p/'all_markers.rpt').read_text()
 roi=[(p/f'roi_{j:02d}.rpt').read_text() for j in range(len(cases))]
 def rules(s):return dict(Counter(re.findall(r'^violation type: (.+)$',s,re.M)))
 results[name]={'global_report_rule_counts':rules(globalreport),'global_report_bytes':len(globalreport),'full_native_ROI_rule_counts':[rules(s) for s in roi],'cases':out,'global_report_path':str(p/'all_markers.rpt')}
 if name in ['qwen','sc2']:assert out[name]['whole_graph_connected']
 if name=='missing_bridge':assert not out[name]['whole_graph_connected'] and out[name]['connectivity']['VDD']['components']==2
 if name=='short_bridge':assert out[name]['actual_crossnet_overlaps'] and not out[name]['whole_graph_connected']
(P/'analysis.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({k:{'native_global':v['global_report_rule_counts'],'graph':{c:r['whole_graph_connected'] for c,r in v['cases'].items()}}for k,v in results.items()},indent=2))
