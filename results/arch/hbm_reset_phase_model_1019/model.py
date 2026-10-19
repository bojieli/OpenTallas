import json,gzip,re,hashlib
from pathlib import Path
O=Path(__file__).parent
B=O/'inputs'
def block(t,start):
 k=t.index('{',start);n=1;j=k+1
 while n:n+=(t[j]=='{')-(t[j]=='}');j+=1
 return t[start:j]
roles={};arcs=[]
for p in sorted(B.glob('*.lib*')):
 raw=p.read_bytes();t=gzip.decompress(raw).decode() if p.suffix=='.gz' else raw.decode();co='TT' if '_TT_' in p.name else 'FF'
 for name in ['BUFx12f','DFFASRHQNx1','INVx1','INVx6','TIEHIx1']:
  full=name+'_ASAP7_75t_R';m=re.search(r'cell\s*\(\s*'+full+r'\s*\)',t)
  if not m:continue
  c=block(t,m.start());rr={'lib_sha256':hashlib.sha256(raw).hexdigest(),'lib':p.name,'area':float(re.search(r'\barea\s*:\s*([0-9.]+)',c)[1]),'pins':{}};roles[co+':'+name]=rr
  for pm in re.finditer(r'\bpin\s*\(\s*(\w+)\s*\)',c):
   q=block(c,pm.start());prop={k:re.findall(r'\b'+k+r'\s*:\s*([^;]+)',q)[:1] for k in ['direction','function','capacitance','max_capacitance']};rr['pins'][pm[1]]=prop
   for tm in re.finditer(r'\btiming\s*\(',q):
    a=block(q,tm.start());meta={k:re.findall(r'\b'+k+r'\s*:\s*([^;]+)',a)[:1] for k in ['related_pin','timing_type','timing_sense','when']}
    for tb in re.finditer(r'\b(cell_rise|cell_fall|rise_transition|fall_transition|rise_constraint|fall_constraint)\s*\(',a):
     z=block(a,tb.start());axes={k:[float(v) for v in s.split(',')] for k,s in re.findall(r'(index_[123])\s*\(\s*"([^"]+)"',z)}
     vals=re.search(r'values\s*\((.*?)\)\s*;',z,re.S)
     if not vals:continue
     nums=[float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',vals[1])]
     arcs.append(dict(corner=co,cell=name,pin=pm[1],table=tb[1],axes=axes,minimum=min(nums),maximum=max(nums),**meta))
(O/'native_tables.json').write_text(json.dumps({'roles':roles,'arcs':arcs},indent=1)+'\n')
def span(co,cell,pin,tt,table):
 a=[x for x in arcs if x['corner']==co and x['cell']==cell and x['pin']==pin and x['timing_type']==[tt] and x['table']==table]
 return [min(x['minimum'] for x in a),max(x['maximum'] for x in a)] if a else None
out={}
for co in ['TT','FF']:
 d={}
 for pin,tt,tab in [('RESETN','recovery_rising','rise_constraint'),('RESETN','removal_rising','rise_constraint'),('RESETN','min_pulse_width','fall_constraint'),('D','setup_rising','rise_constraint'),('D','hold_rising','rise_constraint'),('CLK','min_pulse_width','rise_constraint'),('CLK','min_pulse_width','fall_constraint')]:d[pin+':'+tt+':'+tab]=span(co,'DFFASRHQNx1',pin,tt,tab)
 for cell,pin,tt in [('DFFASRHQNx1','QN','rising_edge'),('INVx1','Y','combinational'),('INVx6','Y','combinational'),('BUFx12f','Y','combinational')]:
  for tab in ['cell_rise','cell_fall','rise_transition','fall_transition']:d[cell+':'+tab]=span(co,cell,pin,tt,tab)
 out[co]=d
(O/'global_native_grid_bounds.json').write_text(json.dumps(out,indent=1)+'\n')
p=json.load(open(B/'compressed_topology.json'));ids={v['id']:v for v in p}
rcs={'platform_M6':(.0118796,.187426),'platform_M7':(.0125096,.162979),'historical_calibrated_M6_M7':(.014,.105)}
rr={}
for name,(r,c) in rcs.items():
 rows=[]
 for x in p:
  # Trunk branches are actual recorded polylines; adding 3um per branch is conservative contact allowance. Leaf branches local only not included.
  lengths=[ids[i]['path_um']+3 for i in x['children']];L=sum(lengths)
  for co in ['TT','FF']:
   cap=float(roles[co+':DFFASRHQNx1']['pins']['RESETN']['capacitance'][0]);C=c*L+cap*x['trunk_transparent_loads']
   rows.append({'id':x['id'],'corner':co,'wire_sum_um':L,'wire_fF':c*L,'native_reset_input_fF':cap*x['trunk_transparent_loads'],'total_fF':C,'INV1_over46p08':C>46.08,'INV6_over368p64':C>368.64,'longest_branch_um':max(lengths,default=0),'wire_elmore_ps_upper':r*L*(c*L/2+cap*x['trunk_transparent_loads'])})
 rr[name]={'r_kohm_per_um':r,'c_fF_per_um':c,'rows':rows,'INV1_overcap_count':sum(v['INV1_over46p08'] for v in rows),'INV6_overcap_count':sum(v['INV6_over368p64'] for v in rows),'max_total_fF':max(v['total_fF'] for v in rows),'max_trunk_wire_sum_um':max(v['wire_sum_um'] for v in rows),'max_lumped_elmore_ps':max(v['wire_elmore_ps_upper'] for v in rows)}
(O/'trunk_rc_model.json').write_text(json.dumps(rr,indent=1)+'\n')
print(json.dumps(out,indent=1));print(json.dumps({n:{k:v for k,v in o.items() if k!='rows'} for n,o in rr.items()},indent=1))
