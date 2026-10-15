#!/usr/bin/env python3
import collections,hashlib,json,math,re
from pathlib import Path
p=Path(__file__).resolve().parent
g=json.loads((p.parent/'graph.json').read_text())
lib=(p/'asap7_rvt_tt.lib').read_text()
areas={}
for m in re.finditer(r'\bcell\s*\(\s*(\S+?)\s*\)\s*\{',lib):
 area=re.search(r'\barea\s*:\s*([\d.]+)',lib[m.end():]);areas[m[1]]=float(area[1])
rows=[]
for file in sorted(p.glob('*.mapped.json')):
 top=file.name.split('.')[0];mapped=json.loads(file.read_text());generic=json.loads((p/(top+'.generic.json')).read_text())
 def census(j):
  cells=collections.Counter();seq=collections.Counter()
  def walk(module):
   for cell in j['modules'][module]['cells'].values():
    t=cell['type']
    if t in j['modules']:walk(t)
    elif t!='$scopeinfo':
     cells[t]+=1
     if t.startswith(('$_DFF','$_SDFF')):seq[t]+=1
  walk(top);return cells,seq
 mc,_=census(mapped);gc,seq=census(generic)
 unknown={k:v for k,v in mc.items() if k not in areas}
 assert not unknown,(top,unknown)
 area=sum(areas[k]*v for k,v in mc.items())
 log=(p/(top+'.log')).read_text();reported=float(re.findall(r'Chip area for (?:top )?module .*?:\s*([\d.]+)',log)[-1]);assert abs(area-reported)<1e-5,(top,area,reported)
 pins=g['module_port_boundaries'][top]['declared_port_bits']
 # Lower-level outline study only: these assumptions do not constitute pin-fit or legalization.
 core=math.sqrt(area/0.4);pin_side=pins*0.096/(4*0.8);side=math.ceil(max(core,pin_side)/1.08)*1.08
 params={'MUT':0}
 if top=='s81_static_vm_boundary':params['PINCAP']=1
 if top=='s81_static_raw_vm_rows':params['REGISTER_VM_WRITES']=0
 if top=='s81_static_host_queue':params['DEPTH']=16
 rows.append(dict(module=top,parameters=params,sequential_bit_cells=sum(seq.values()),sequential_cell_types=dict(seq),mapped_cell_area_um2=round(area,8),mapped_cell_count=sum(mc.values()),unmapped_cell_types=unknown,declared_rtl_port_bits=pins,outline_study=dict(status='SITE_ALIGNED_AREA_AND_AGGREGATE_PIN_BOUND_ONLY_NOT_LEGALIZED',area_square_side_um=core,aggregate_pin_square_side_um=pin_side,provisional_square_core_um=[round(side,5)]*2,provisional_square_with_5p4_margin_um=[round(side+10.8,5)]*2),evidence=dict(generic_json=file.name.replace('.mapped.','.generic.'),mapped_json=file.name,log=top+'.log',script=top+'.ys')))
result=dict(schema='s81.actual-collective-module-synthesis.v1',source_commit=g['source_commit'],tool='Yosys 0.67 2d1509d1b in openroad/orfs:latest',technology='ASAP7 RVT TT NLDM, real sequential library 220123 plus four combinational libraries',library_sha256=hashlib.sha256(lib.encode()).hexdigest(),library_cell_area_um2=areas,scope='Exact-source module synthesis with actual parent parameters. No source edits, clock/reset/latency transformations, placement, CTS or routing. Full DFF legalization uses physical asynchronous-set/reset cells. Module-only counts exclude surrounding wrapper ownership.',outline_study_assumptions=dict(target_cell_utilization=0.4,M4_pitch_um=0.048,pin_spacing_tracks=2,available_edge_fraction=0.8,edge_assignment='hypothetical balanced across four sides; no actual pin-fit test',alignment_grid_um=1.08,site_um=[0.054,0.270],margin_each_side_um=5.4,warning='Provisional geometric study. Fixed face assignment, PDN, CTS, congestion, pin escape, access DRC and all incident neighbors can require larger or nonsquare outlines.'),modules=rows)
by={r['module']:r for r in rows}
r=by['s81_static_hc_scalar_reduce'];a=by['s81_static_hc_scalar_assemble'];result['hc16_summary']=dict(arithmetic_instances=16,assembly_instances=16,pair_mapped_cell_area_um2=round(r['mapped_cell_area_um2']+a['mapped_cell_area_um2'],8),all32_mapped_cell_area_um2=round(16*(r['mapped_cell_area_um2']+a['mapped_cell_area_um2']),8),pair_storage_bits=r['sequential_bit_cells']+a['sequential_bit_cells'],all32_storage_bits=16*(r['sequential_bit_cells']+a['sequential_bit_cells']),additional_parent_local_reset_bits=32,combined_physical_pin_count=None,combined_outline=None)
(p/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
result['container_image_id']='sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34'
mul={'s81_static_hc_scalar_reduce':16,'s81_static_hc_scalar_assemble':16,'s81_static_fmt1_lane_dynamic':3,'s81_static_raw_fmt1_lane':5}
result['known_standalone_module_instance_area_subtotal_um2']=round(sum(r['mapped_cell_area_um2']*mul.get(r['module'],1) for r in rows),8)
result['area_subtotal_exclusions']=['current calendar and its three ROM hardmacros','HC metadata/control root','surrounding wrapper clock/reset/rank configuration and fault/status ownership not inside measured standalone modules','CTS buffers, PDN, fill, routing and pin escape']
result['area_subtotal_warning']='Standalone module sum before shared optimization or hard-cut boundary selection; not complete collective area.'
(p/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
for r in rows:print(r['module'],r['sequential_bit_cells'],r['mapped_cell_area_um2'],r['outline_study']['provisional_square_with_5p4_margin_um'])
