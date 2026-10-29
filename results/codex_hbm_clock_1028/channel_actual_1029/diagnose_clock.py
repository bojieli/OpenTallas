from pathlib import Path
import json,re,collections,math
R=Path(__file__).parent;t=json.load(open(R/'channel_sm3_v2/tree_frozen.json'));xy=t['sites'];po=t['parent_of'];a={}
for l in(R/'nodes_TT.txt').read_text().splitlines():
 v=l.split();a[v[1]]=dict(late_rise=float(v[2]),late_fall=float(v[3]),early_rise=float(v[4]),early_fall=float(v[5]),input_slew_rise=float(v[6]),output_slew_rise=float(v[7]))
v=(R/'channel_sm3_v2/ctree.v').read_text();outputs={n:net for n,net in re.findall(r'CKINV\S+\s+(\S+)\s*\(\.A\([^)]*\),\s*\.Y\(([^)]*)\)',v)};guides={};net=None
for l in(R/'route_TT.guide').read_text().splitlines():
 v=l.split()
 if len(v)==1 and v[0]not in('(',')'):net=v[0];guides[net]=[]
 elif len(v)==5:
  x0,y0,x1,y1=map(lambda x:float(x)/1000,v[:4]);guides[net].append(dict(layer=v[4],rect=[x0,y0,x1,y1],guide_long_axis_um=max(x1-x0,y1-y0)))
co=[11.034201,.169972,.000058];edges=[]
for c,p in po.items():
 L=abs(xy[c][0]-xy[p][0])+abs(xy[c][1]-xy[p][1]);meas=a[c]['late_rise']-a[p]['late_fall'];model=co[0]+co[1]*L+co[2]*L*L;net=outputs[p];g=guides.get(net,[]);edge=dict(child=c,parent=p,planned_pin_origin_span_um=L,actual_late_increment_ps=meas,early_fit_increment_ps=model,late_minus_model_ps=meas-model,parent_slew_ps=a[p]['output_slew_rise'],child_input_slew_ps=a[c]['input_slew_rise'],net=net,fanout=sum(q==p for q in po.values()),guide_layers=dict(collections.Counter(z['layer']for z in g)),guide_span_estimate_um=sum(z['guide_long_axis_um']for z in g),parent_cell='CKINVDCx16_ASAP7_75t_R',child_cell='CKINVDCx16_ASAP7_75t_R');edges.append(edge)
rows=json.load(open(R/'actual_clock_arrivals.json'))['TT']['rows'];modelrows={r['port']:r['delay_ps']['TT']for r in json.load(open(R/'channel_sm3_v2/summary.json'))['rows']};worst=sorted(rows,key=lambda r:-(r['late_rise_ps']-modelrows[r['port']]))[:5];report=[]
for rr in worst:
 tap=next(x for x in t['taps']if x['port']==rr['port']);driver=t['node_buf'][str(tap['node'])];chain=[driver]
 while chain[-1]in po:chain.append(po[chain[-1]])
 cs=set(chain);ee=[e for e in edges if e['child']in cs];q=xy[driver];tail=abs(q[0]-tap['xy'][0])+abs(q[1]-tap['xy'][1]);report.append(dict(port=rr['port'],actual_adjusted_late_ps=rr['late_rise_ps'],model_ps=modelrows[rr['port']],residual_ps=rr['late_rise_ps']-modelrows[rr['port']],driver=driver,native_path_cells=len(chain),tap_pin_origin_tail_um=tail,tap_load_fF=3.,worst_increment_residuals=sorted(ee,key=lambda e:-e['late_minus_model_ps'])[:6]))
out=dict(scope='same-source topology native GRT TT diagnosis; guide lengths are guide-rectangle estimates, not RCX routed wire length',native_cells=len(a),frozen_cells=len(xy),top5=report,largest_edge_residuals=sorted(edges,key=lambda e:-e['late_minus_model_ps'])[:15]);(R/'clock_residual_diagnosis.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(report,indent=1))
