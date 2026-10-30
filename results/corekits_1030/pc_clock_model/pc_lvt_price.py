import json,pathlib,re,bisect
p=pathlib.Path(__file__).parent;d=json.loads((p/'pc_clock_family_source_model.json').read_text());lib=json.loads((p/'lvt_raw_tables.json').read_text())['cells'];segs=json.loads((p/'pc_clock_segment_lengths.json').read_text());log=(p/'pc_actual_native.log').read_text();rc={m:float(r) for m,r in re.findall(r'set_layer_rc -layer (\S+) -resistance (\S+)',(p/'pc_selected_RC.tcl').read_text())}
def table(t,x,y):
 a,b,v=t;i=max(0,min(len(a)-2,bisect.bisect_right(a,x)-1));j=max(0,min(len(b)-2,bisect.bisect_right(b,y)-1));u=(x-a[i])/(a[i+1]-a[i]);w=(y-b[j])/(b[j+1]-b[j]);return (1-u)*((1-w)*v[i][j]+w*v[i][j+1])+u*((1-w)*v[i+1][j]+w*v[i+1][j+1])
out={'status':'SOURCE NLDM PRICE ONLY; not STA or physical qualification','candidate_count':d['candidate_count'],'lvt_pct':d['lvt_percent'],'assumptions':['Both rise/fall NLDM; linear extrapolation below table cap23.04fF','Original incoming slew envelope5..320ps held; no credit for propagated slew improvement','All candidate child BUF/dummy Cin increases charged; FF leaf fanout Cin unchanged','Full wire resistance times added Cin is conservative lumped wire penalty; same clock topology','No RC coefficient/SDC/guard changes; actual native LVT STA still required'],'paths':{}}
for target,chain in d['current_paths'].items():
 section=log[log.rfind('Startpoint: i_next['+target+']'):];rows=[]
 for item in chain:
  name=item['instance'];matches=re.findall(r'^\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+[\^v]\s+'+re.escape(name)+r'/Y',section,re.M)
  if not matches:raise ValueError(name)
  fan,cap,slew,delay,at=map(float,matches[0]);fan=int(fan);R=lib['FF:BUFx24_ASAP7_75t_R'];L=lib['FF:BUFx24_ASAP7_75t_L'];dc=(L['capacitance'][0]-R['capacitance'][0])*(0 if item==chain[-1] else fan)
  seg=segs[item['output_net']];wr=sum(rc[k]*v for k,v in seg['layer_um'].items())+sum(n*.0082 for n in seg['vias'].values());penalty=wr*dc
  gains=[table(R['tables'][arc],s,cap)-table(L['tables'][arc],s,cap+dc)-penalty for s in (5,10,20,40,80,160,320) for arc in ('cell_rise','cell_fall')]
  rows.append({'instance':name,'cap_ff':cap,'deltaCin_ff':dc,'wire_penalty_ps':penalty,'same_slew_gain_min_ps':min(gains),'same_slew_gain_max_ps':max(gains)})
 out['paths'][target]={'stages':len(rows),'FF_same_slew_price_min_ps':sum(r['same_slew_gain_min_ps'] for r in rows),'FF_same_slew_price_max_ps':sum(r['same_slew_gain_max_ps'] for r in rows),'stages_detail':rows}
(p/'pc_lvt_price.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:{x:y for x,y in v.items() if x!='stages_detail'} for k,v in out['paths'].items()}))
