from pathlib import Path
import re,json,shutil
R=Path.cwd();d=json.load(open(R/'write_geometry.json'));old=R/'initial_source_point_lowerbound.json'
if not old.exists():shutil.copyfile(R/'write_geometry.json',old)
io=(R/'io.tcl').read_text();sizes={n:(float(w),float(h))for n,w,h in re.findall(r'place_pin -pin_name \{([^}]+)\}[^\n]*-pin_size \{([\d.]+) ([\d.]+)\}',io)}
for q in d['source_fanouts']:
 if not q.get('source_rectangle_extent_included'):
  w,h=sizes[q['source_ABI']];q['optimistic_target_rectangle_minimax_lowerbound_um']=max(0,q['optimistic_target_rectangle_minimax_lowerbound_um']-(w+h)/2);q['source_rectangle_extent_included']=True
# GEN pins.json and io.tcl must be the identical unqualified public pin assignment.
centres={n:(float(x),float(y))for n,x,y in re.findall(r'place_pin -pin_name \{([^}]+)\}[^\n]*-location \{([\d.]+) ([\d.]+)\}',io)};pins=json.load(open(R/'pins.json'));assert {f"{p['bus']}[{p['bit']}]"for p in pins}==set(centres)
assert all(centres[f"{p['bus']}[{p['bit']}]"][0]-sizes[f"{p['bus']}[{p['bit']}]"][0]/2-1e-6<=p['x']<=centres[f"{p['bus']}[{p['bit']}]"][0]+sizes[f"{p['bus']}[{p['bit']}]"][0]/2+1e-6 and centres[f"{p['bus']}[{p['bit']}]"][1]-sizes[f"{p['bus']}[{p['bit']}]"][1]/2-1e-6<=p['y']<=centres[f"{p['bus']}[{p['bit']}]"][1]+sizes[f"{p['bus']}[{p['bit']}]"][1]/2+1e-6 for p in pins)
d['source_bits_continuously_impossible_even_with_repositioning']=sum(q['optimistic_target_rectangle_minimax_lowerbound_um']>405+1e-6 for q in d['source_fanouts']);d['max_optimistic_target_rectangle_minimax_lowerbound_um']=max(q['optimistic_target_rectangle_minimax_lowerbound_um']for q in d['source_fanouts']);d['GEN_declared_anchor_inside_IO_rectangle']=True;d['GEN_pin_anchor_semantics']='6038 data pins.json boundary anchors differ from inward IO rectangle centres by <=0.096um; all6040 anchors lie inside corresponding GEN IO rectangle. Clock/reset are centre entries.';d['continuous_lowerbound_basis']='target-centre minimax minus maximum target rectangle half-L1diameter minus actual source rectangle half-L1diameter; optimistic even allowing different contacts on each wire'
(R/'write_geometry.json').write_text(json.dumps(d,indent=2)+'\n');print(d['source_bits_continuously_impossible_even_with_repositioning'],d['max_optimistic_target_rectangle_minimax_lowerbound_um'])
