import json,re,sys
from pathlib import Path
w=Path('/srv/opentallas-scratch2/claude/wt/codex-head-1351');sys.path.insert(0,str(w/'tools/die_plan'));import schema as S
out=w/'results/head_native_1351';raw=json.loads((out/'die_plan_native_entries.json').read_text());P=S.Plan(raw);census=json.loads((out/'signed_view_census.json').read_text());types={}
def block(text,pattern):
 m=re.search(pattern,text);assert m,pattern
 start=m.end();depth=1;i=start
 while depth:
  depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i-1]
def libpin(text,pin):return block(text,r'\bpin\s*\(\s*"?'+re.escape(pin)+r'"?\s*\)\s*\{')
for k in ('A','B'):
 mod='ot_s81hd_elem'+k+'_cv';d=out/'signed_views'/mod;lef=(d/(mod+'.lef')).read_text();pins={}
 for pn in ('ft_mesh_i','ft_mesh_o','ft_mstrap_i'):
  t=re.search(r'\bPIN\s+'+pn+r'\s+(.*?)\bEND\s+'+pn+r'\b',lef,re.S)[1];rc=re.search(r'RECT\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)',t);rect=list(map(float,rc.groups()));layer=re.search(r'LAYER\s+(\w+)',t)[1];pins[pn]=dict(direction=re.search(r'DIRECTION\s+(\w+)',t)[1],layer=layer,rect_um=rect,center_um=[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2],capacitance_fF={})
 arcs={}
 for corner in ('tt','ff'):
  lib=(d/(mod+'_'+corner+'.lib')).read_text();assert re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*fF\s*\)',lib);assert re.search(r'time_unit\s*:\s*"1ps"',lib)
  for pn in pins:
   b=libpin(lib,pn);pins[pn]['capacitance_fF'][corner]=float(re.search(r'\bcapacitance\s*:\s*([0-9.eE+-]+)',b)[1])
  b=libpin(lib,'ft_mesh_o');assert re.search(r'related_pin\s*:\s*"ft_mesh_i"',b)
  tables={}
  for key in ('cell_rise','cell_fall','rise_transition','fall_transition'):
   tb=block(b,r'\b'+key+r'\s*\([^)]*\)\s*\{');tables[key]=dict(index_output_load_fF=[float(v) for v in re.search(r'index_1\s*\(\s*"([^"]+)"',tb)[1].split(',')],values_ps=[float(v) for v in re.search(r'values\s*\(\s*"([^"]+)"',tb)[1].split(',')])
  arcs[corner]=dict(nldm=tables,reference_signed_standalone_delay_ps=next(a[corner+'_ps'] for a in census['views'][mod]['arcs'] if a['source']=='ft_mesh_i'))
 types[mod]=dict(pins=pins,mesh_arc=arcs,functional_pin_register_mean_ps=census['views'][mod]['clock_pin_latency_ps'],note='M5 native core ports; M7 wrapper adapter pads connect through partition-owned M6/M5 access. FT buffer arc is OUTSIDE the functional ft_mstrap_i measured mean and must be timed separately.')
rows=[];tile=raw['partition_types']['hd_tile'];ports={p['name']:p for p in tile['infra_ports']};taps=[t for t in tile['clock']['taps'] if t.get('kind')=='core']
for part in raw['partitions']:
 if part['type']!='hd_tile':continue
 for h in tile['hard_cores']:
  typ=h['module'];idx=4 if 'elemB' in typ else int(h['inst'][-1]);sw,sh=h['outline_um'];hx,hy=h['origin_um'];dx,dy=h.get('track_offset_um',[0,0]);ori=h.get('orient','R0');mapping={}
  for pn,pin in types[typ]['pins'].items():
   x,y=pin['center_um'];x=sw-x if ori in ('MY','R180') else x;y=sh-y if ori in ('MX','R180') else y;xy=[hx+dx+x,hy+dy+y];mapping[pn]=dict(core_xy_um=pin['center_um'],type_xy_um=xy,die_xy_um=list(P.to_die(part['name'],xy)),native_layer=pin['layer'])
  inp=ports[f'hci{idx}_mesh_i'];op=ports[f'hci{idx}_mesh_o'];ftout=mapping['ft_mesh_o']['type_xy_um'];func=mapping['ft_mstrap_i']['type_xy_um']
  rows.append(dict(part=part['name'],macro_inst=h['inst'],module=typ,part_orient=P.orient(part['name']),core_orient=ori,mesh_input_port=inp['name'],mesh_output_port=op['name'],functional_entry='clk_c'+str(idx),actual_pins=mapping,wrapper_M7_input_xy_um=inp['xy_um'],wrapper_M7_output_xy_um=op['xy_um'],local_output_to_functional_pin_manhattan_um=round(abs(ftout[0]-func[0])+abs(ftout[1]-func[1]),6),contract='actual continuous mesh → ft_mesh_i → existing signed FT buffer arc → ft_mesh_o → short local wire → ft_mstrap_i → signed functional core tree; no external duplicate local stub'))
r=dict(schema='opentallas.head.ft_mesh_endpoint_contract.v1',source='c41625cb88 signed residual4 views from5e10e34dea',units=dict(capacitance='fF',time='ps',coordinates='um'),types=types,sinks=rows,counts=dict(cores=len(rows),mesh_input_Cin_tt_fF=sum(types[r['module']]['pins']['ft_mesh_i']['capacitance_fF']['tt'] for r in rows)),no_cycles_added=True,provider_graph_supplied=False,arc_load_note='Signed reference FT delays are standalone measurements. Die STA must use the NLDM arc with actual wire+ft_mstrap_i load and account separately for local wire; no fanout-independent25ps constant is assumed.')
(out/'ft_mesh_endpoint_contract.json').write_text(json.dumps(r,indent=1)+'\n');print('MAPPED_SINKS',len(rows));print('INPUT_CIN_TT_TOTAL_fF',r['counts']['mesh_input_Cin_tt_fF'])
for mod,v in types.items():print(mod,{p:(d['layer'],d['center_um'],d['capacitance_fF']) for p,d in v['pins'].items()}, {c:v['mesh_arc'][c]['reference_signed_standalone_delay_ps'] for c in ('tt','ff')})
