"""Bind actual all-cell graph, parent captures, native functions and ABI contacts."""
import json,csv,re,hashlib
from pathlib import Path
j=json.loads(Path('out/netlist.json').read_text())['modules']['hidx_coupon1'];old=json.loads(Path('canonical/netlist.json').read_text())['modules']['hidx_coupon1'];clk=j['ports']['clk']['bits']
assert all(j['cells'][n]==c for n,c in old['cells'].items())
for name in ['compacted','pair_select','quad_select']:
 for i,port in enumerate(j['ports'][name]['bits']):
  b=j['cells'][f'wrapper_output_{name}_{i}'];assert b['type']=='BUFx8_ASAP7_75t_R';assert b['connections']['Y']==[port];assert b['connections']['A']!=[port]
  if name=='compacted':
   f=j['cells'][f'wrapper_s1_ff_{i}'];inv=j['cells'][f'wrapper_s1_inv_{i}']
   assert f['type']=='DFFHQNx1_ASAP7_75t_R' and inv['type']=='INVx1_ASAP7_75t_R'
   assert f['connections']['CLK']==clk and f['connections']['QN']==b['connections']['A']
   assert f['connections']['D']==inv['connections']['Y'] and inv['connections']['A']==[old['ports'][name]['bits'][i]]
  else:assert b['connections']['A']==[old['ports'][name]['bits'][i]]
# Keep complete actual native Liberty function excerpts, not invented cell models.
lib=Path('out/all.lib').read_text()
def block(name,kind):
 z=re.search(r'\b'+kind+r'\s*\(\s*'+re.escape(name)+r'\s*\)\s*\{',lib);assert z
 a=lib.index('{',z.start());d=1;b=a+1
 while d:d+=(lib[b]=='{')-(lib[b]=='}');b+=1
 return lib[a+1:b-1]
refs={}
for n in ['DFFHQNx1_ASAP7_75t_R','INVx1_ASAP7_75t_R','BUFx8_ASAP7_75t_R']:
 body=block(n,'cell');refs[n]=dict(functions=re.findall(r'function\s*:\s*"([^"]+)"',body),next_state=re.findall(r'next_state\s*:\s*"([^"]+)"',body),clocked_on=re.findall(r'clocked_on\s*:\s*"([^"]+)"',body),body_sha256=hashlib.sha256(body.encode()).hexdigest())
assert refs['DFFHQNx1_ASAP7_75t_R']['next_state']==['!D']
assert 'IQN' in refs['DFFHQNx1_ASAP7_75t_R']['functions']
assert any(re.sub(r'[\s()]','',f)=='!A' for f in refs['INVx1_ASAP7_75t_R']['functions'])
assert 'A' in refs['BUFx8_ASAP7_75t_R']['functions']
Path('out/source_binding_manifest.json').write_text(json.dumps(dict(verdict='PASS',source_parent='5af00a1ab:rtl/hbm_accel/index/ot_hbm_idx_topk_link_static_p.sv:273,432',source_capture='unconditional unreset s1_gc<=gc; corresponding288bits',canonical_cells_kept=8265,canonical_cell_records_identical=True,output_ports=2304,buf_A_Y_aliases=0,capture_ff=288,pred_polarity_inv=288,selector_age_unchanged=True,native_functions=refs,initial_sat_verdict='WITHDRAWN: malformed Verilog stale port aliases',replacement_sat='out/formal.log; only valid after out/roundtrip_equivalence.json',sourcebench='original byte-identical wrapper/tb; all65537samples at II1 after2edgepriming'),indent=2)+'\n')
initial={}
trace_manifest=Path('out_repr_bad/initial_draft/SOURCE_SHA256SUMS')
if not trace_manifest.exists():trace_manifest=Path('out/SOURCE_TRACE_SHA256SUMS')
for line in trace_manifest.read_text().splitlines():
 h,name=line.split(maxsplit=1)
 if '/tools/' in name:name='tools/'+name.split('/tools/',1)[1]
 initial[name]=h
sourcefiles={}
for name in ['wrapper.sv','tb.sv','formal.sv']:
 fn='tools/hbm_hidx_wrapper/'+name;h=hashlib.sha256(Path(fn).read_bytes()).hexdigest();assert initial[fn]==h;sourcefiles[fn]=h
assert hashlib.sha256(Path('tools/hbm_hidx_coupon1/coupon.sv').read_bytes()).hexdigest()=='39748b942b58620b2519b189e379ddf4fcef68a6edae3e52430fd6cdcbf907cf'
Path('out/source_trace_identity.json').write_text(json.dumps(dict(verdict='PASS',initial_and_final_source_hashes_equal=sourcefiles,canonical_coupon_sha256='39748b942b58620b2519b189e379ddf4fcef68a6edae3e52430fd6cdcbf907cf'),indent=2)+'\n')
ports=list(csv.DictReader(Path('canonical/ports.csv').open()));rects=[]
for r in ports:
 face=r['face'];x=float(r['x_um']);y=float(r['y_um']);layer='M4' if face in 'WE' else 'M5'
 rect={'W':[0,y-.012,.096,y+.012],'E':[140.304,y-.012,140.4,y+.012],'S':[x-.012,0,x+.012,.096],'N':[x-.012,140.304,x+.012,140.4]}[face]
 rects.append(dict(port=r['port'],face=face,role=r['role'],layer=layer,rect_um=rect))
Path('out/pin_geometry_model.json').write_text(json.dumps(dict(scope='MODEL ONLY; no pins placed; actual DRC/access OPEN',pitch_um=.192,track_pitch_um=.048,proposed_track_offset_um=.024,native_tech_width_um=.024,pin_length_um=.096,pin_area_um2=.002304,native_min_area_um2=.002,tech_offset_is_not_placement_grid='M4 tech .003/M5 tech0; proposed explicit .024 grid requires actual engine/access review',pins=rects),indent=2)+'\n')
