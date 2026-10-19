import json,re,pathlib
p=pathlib.Path(__file__).parent
d=json.load(open(p/'source_bound.json'));summary={}
for co,v in d.items():
 text=(p/('source_dcalc_'+co+'.log')).read_text();measured={}
 for m in re.finditer(r'^SOURCE_DCALC ([^\n]+) (min|max)\n(.*?)(?=^SOURCE_DCALC |^READONLY_|\Z)',text,re.M|re.S):
  pn,mm,t=m.groups();arcs={}
  for a in re.finditer(r'CLK \^ -> QN ([\^v])\n(.*?)(?=CLK \^ -> QN|\Z)',t,re.S):
   dl=re.search(r'^Delay = ([\d.]+)',a[2],re.M);arcs['rise' if a[1]=='^' else 'fall']=float(dl[1])
  measured.setdefault(pn,{})[mm]=arcs
 bs=v['boundary_sources'];cqdelta=[]
 for b in bs:
  pn=b['source']['pin'];b['native_original_CQ_ps']=measured[pn]
  for edge in ['rise','fall']:
   cqdelta.append({'pin':pn,'edge':edge,'min_delta_ps':b['new_ff']['range_ps']['cell_'+edge][0]-measured[pn]['min'][edge],'max_delta_ps':b['new_ff']['range_ps']['cell_'+edge][1]-measured[pn]['max'][edge]})
 ss={'boundary_count':len(bs),'source_count':len(measured),'max_new_source_cap_ff':max(max(b['new_total_ff']) for b in bs),'max_original_wire_cap_ff':max(max(b['source']['wire_ff']) for b in bs),'max_actual_clock_slew_ps':max(max(x for vs in b['source']['clock_slew_ps'].values() for x in vs) for b in bs),'max_new_QN_slew_ps':max(max(b['new_ff']['range_ps'][k][1] for k in ['rise_transition','fall_transition']) for b in bs),'max_INV6_lumped_slew_at114p8_ff_ps':max(max(b['new_INV6_at_worst_measured114p8_ff']['range_ps'][k][1] for k in ['rise_transition','fall_transition']) for b in bs),'CQ_delta_bounds_ps':[min(x['min_delta_ps'] for x in cqdelta),max(x['max_delta_ps'] for x in cqdelta)],'CQ_deltas':cqdelta,'cones':{}}
 probe=(p/('source_probe_'+co+'.log')).read_text()
 for n,c in v['changed_cones'].items():
  changes=[]
  for source in c['sources']:
   pn=source['source']['pin'];source['native_original_CQ_ps']=measured[pn];changes.append(source)
  t=re.search(r'^CONE '+n+r'\n(.*?)(?=^CONE |^GATE_INPUT |\Z)',probe,re.M|re.S)[1];adjusted=[]
  for path in re.split(r'(?=Startpoint:)',t):
   if 'Path Type: min' not in path:continue
   start=re.search(r'Startpoint: (\S+)',path)[1];source=next(s for s in changes if s['source']['pin']==start+'/QN');rows=[]
   for line in path.splitlines():
    if ('/QN (' in line and start+'/QN' in line) or ('/Y (' in line and c['old_master'] in line):
     # Last two numeric columns precede the edge and full native pin name.
     m=re.search(r'(-?[\d.]+)\s+(-?[\d.]+)\s+[\^v]\s+(\S+)',line)
     if m:rows.append((m[3],float(m[1])))
   if len(rows)!=2:raise RuntimeError((n,rows))
   oldcq=next(x[1] for x in rows if x[0].endswith('/QN'));oldgate=next(x[1] for x in rows if x[0].endswith('/Y'));newcq=min(source['new_ff']['range_ps']['cell_rise'][0],source['new_ff']['range_ps']['cell_fall'][0]);newgate=min(c['new_gate']['range_ps']['cell_rise'][0],c['new_gate']['range_ps']['cell_fall'][0]);sl=float(re.search(r'(-?[\d.]+)\s+slack \(',path)[1]);endpoint=re.search(r'Endpoint: (\S+)',path)[1]
   adjusted.append({'endpoint':endpoint,'existing_native_min_slack_ps':sl,'original_CQ_ps':oldcq,'original_gate_ps':oldgate,'conditional_new_CQ_min_ps':newcq,'conditional_new_gate_min_ps':newgate,'conditional_slack_fixed_wire_and_check_ps':sl+newcq-oldcq+newgate-oldgate})
  ss['cones'][n]={'actual_load_ff':c['actual_load_ff'],'existing_min_slack_ps':c['existing_native_slack_minimum_ps']['min'],'minimum_conditional_slack_fixed_wire_and_check_ps':min(x['conditional_slack_fixed_wire_and_check_ps'] for x in adjusted),'paths':adjusted,'warning':'MODEL only: actual wire slew/delay and recovery/removal/hold checks change with waveform; not a native successor PASS'}
 summary[co]=ss
json.dump(d,open(p/'source_bound_with_native_CQ.json','w'),indent=2)
json.dump(summary,open(p/'summary.json','w'),indent=2)
for co,s in summary.items():
 print(co,{k:v for k,v in s.items() if k not in ['CQ_deltas','cones']})
 for n,c in s['cones'].items():print(n,c['existing_min_slack_ps'],c['minimum_conditional_slack_fixed_wire_and_check_ps'])
