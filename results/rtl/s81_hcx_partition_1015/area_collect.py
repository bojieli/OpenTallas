import json,functools,collections,pathlib,hashlib
b=pathlib.Path('/srv/opentallas-scratch/codex/s81-hcp-partition-1015-v2'); m=json.loads((b/'mapped_area.json').read_text())['modules']
@functools.lru_cache(None)
def area(name):
 mod=m[name]
 if mod.get('attributes',{}).get('blackbox'):return float(mod['attributes'].get('area',0))
 return sum(area(c['type']) for c in mod.get('cells',{}).values() if c['type'] in m)
owners=collections.Counter()
def walk(name,path,owner):
 for cn,c in m[name].get('cells',{}).items():
  t=c['type'];p=path+'/'+cn
  if t not in m:continue
  if m[t].get('attributes',{}).get('blackbox'):owners[owner]+=area(t)
  else:
   co=p if t=='ot_s81_hcx_hcp_lane8' or 'ot_s81_hcx_hcp_bank' in t or cn=='u_tree' else owner
   walk(t,p,co)
walk('ot_s81_hcx_projection_partition','top','shell')
banks=[v for k,v in owners.items() if '/g_bank[' in k];lanes=[v for k,v in owners.items() if '.g_hard_lane[' in k];tree=[v for k,v in owners.items() if k.endswith('/u_tree')]
r={'scope':'Technology-mapped standardcell area, ASAP7 RVT TT library via Yosys synth/dfflibmap/ABC; area sizing only, no CTS, placement/pinfit, timing or routing qualification','library_cells_area_units':'um^2 (Liberty area)','mapping_script':'map_area.sh','tool_container':'openroad/orfs:asap7lock','source_hierarchy_sha256':hashlib.sha256((b/'hierarchy.json').read_bytes()).hexdigest(),'mapped_standardcell_area_um2':area('ot_s81_hcx_projection_partition'),'hard_owner_standardcell_area_um2':dict(owners),'summary':{'lane8':{'count':len(lanes),'min_stdcell_area_um2':min(lanes),'max_stdcell_area_um2':max(lanes)},'bank':{'count':len(banks),'min_stdcell_area_um2':min(banks),'max_stdcell_area_um2':max(banks),'macro_area_um2_each':8*121.824*62.910+2*94.824*41.040},'tree_stdcell_area_um2':tree,'shell_stdcell_area_um2':owners['shell']},'macro_areas_um2':{'ROM4096x266_each':121.824*62.910,'SRAM128x256_each':94.824*41.040,'total':64*121.824*62.910+16*94.824*41.040},'slot_area_um2':1728*864}
r['standardcell_fraction_after_macro_area'] = r['mapped_standardcell_area_um2']/(r['slot_area_um2']-r['macro_areas_um2']['total'])
(b/'mapped_area_summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['summary'],indent=2));print(r['mapped_standardcell_area_um2'],r['standardcell_fraction_after_macro_area'])
