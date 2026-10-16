"""Read-only actual-PG obstruction audit of proposed DVM parent tracks.

No signal placement, pin grant, or routed qualification is implied. Via routing
rectangles are expanded at their placed coordinates, on every routing layer.
"""
import bisect, hashlib, json, math, sys
from pathlib import Path
import odb

odb_path, fixture, output = map(Path, sys.argv[1:])
# The full source candidate family, not only its first selected200 tracks.
def full_m7_tracks(origin):
 phase=origin%64
 pg=[(2160+300+5400*k+192*j,2160+420+5400*k+192*j) for k in range(13) for j in range(2) if 2160+300+5400*k+192*j<64776-2160]
 return [origin+x for x in range((16-phase)%64,64776,128) if x-16>=576 and x+16<=64776-576 and not any(x+48>a and x-48<b for a,b in pg)]

homes=json.loads((fixture/'column_origins.json').read_text())['homes']
m7=json.loads((fixture/'m6_supported_candidate.json').read_text())['parent_M7_track_requests']
m9_request=json.loads((fixture/'parent_m9_request.json').read_text())
m9=m9_request['columns']
def full_m9_tracks(origin):
 recipe=m9_request['source_PG_recipe_nm'];width,pitch,offset=(recipe[k] for k in ('M9_width','M9_pitch','M9_offset'))
 end=origin+64776
 nominal=[offset+j*pitch/2+k*pitch for j in (0,1) for k in range(math.floor((origin-offset)/pitch)-1,math.ceil((end-offset)/pitch)+1)]
 return [x for x in range(36,end,160) if x>=origin+576 and x<end-576 and all(abs(x-c)>width/2+40+48+20 for c in nominal)]
db=odb.dbDatabase.create(); odb.read_db(db,str(odb_path)); block=db.getChip().getBlock(); units=block.getDbUnitsPerMicron()
if units != 1000: raise ValueError(f'Expected nm DBU, got {units}')
columns={}
for name,h in homes.items():
 inst=block.findInst(name)
 if inst is None: raise ValueError(f'Missing actual column {name}')
 box=inst.getBBox(); expected=[round(h['x']*1000),round(h['y']*1000)]
 if [box.xMin(),box.yMin()] != expected: raise ValueError(f'Origins differ {name}: {[box.xMin(),box.yMin()]} vs {expected}')
 columns[name]=dict(actual_bbox_nm=[box.xMin(),box.yMin(),box.xMax(),box.yMax()],candidate_bbox_nm=[box.xMin(),box.yMin(),box.xMin()+64800,box.yMin()+1473120],
  tracks={'M7':full_m7_tracks(box.xMin()),'M9':full_m9_tracks(box.xMin())},blocked={'M7':set(),'M9':set()},witnesses=[])
ordered_columns=sorted(columns.items(),key=lambda item:item[1]['candidate_bbox_nm'][0])
starts=[c['candidate_bbox_nm'][0] for _,c in ordered_columns]
ends=[c['candidate_bbox_nm'][2] for _,c in ordered_columns]
# Columns are disjoint and equally wide, so both endpoints are ordered.
assert ends==sorted(ends)
counts=dict(wire_rectangles=0,via_rectangles=0,expanded_vias=0)
# 20nm half signal width +48nm conservative nominal separation, matching request.
margin=68

def consume(net,layer,rect,kind):
 if layer not in ('M7','M9'):return
 counts[kind+'_rectangles']+=1
 x0,y0,x1,y1=rect
 for name,col in ordered_columns[bisect.bisect_left(ends,x0-margin):bisect.bisect_right(starts,x1+margin)]:
  bx,by,ex,ey=col['candidate_bbox_nm']
  if x1+margin < bx or x0-margin > ex or y1+margin < by or y0-margin > ey:continue
  tracks=col['tracks'][layer]
  i=bisect.bisect_left(tracks,x0-margin);j=bisect.bisect_right(tracks,x1+margin)
  if j>i:
   col['blocked'][layer].update(tracks[i:j])
   if len(col['witnesses'])<8:col['witnesses'].append(dict(net=net,layer=layer,rect_nm=rect,kind=kind,first_track_nm=tracks[i]))

for net in block.getNets():
 if net.getSigType() not in ('POWER','GROUND'):continue
 for wire in net.getSWires():
  for s in wire.getWires():
   if s.isVia():
    counts['expanded_vias']+=1
    via=s.getBlockVia() or s.getTechVia();x,y=s.getViaXY()
    for b in via.getBoxes():
     lay=b.getTechLayer()
     if lay.getType()=='ROUTING':consume(net.getName(),lay.getName(),[b.xMin()+x,b.yMin()+y,b.xMax()+x,b.yMax()+y],'via')
   else:
    consume(net.getName(),s.getTechLayer().getName(),[s.xMin(),s.yMin(),s.xMax(),s.yMax()],'wire')
for col in columns.values():
 col['available_requested_tracks']={layer:len(col['tracks'][layer])-len(col['blocked'][layer]) for layer in ('M7','M9')}
 col['clear_M7_x_nm']=[x for x in col['tracks']['M7'] if x not in col['blocked']['M7']]
 clear=col['clear_M7_x_nm']
 if len(clear)<200:raise ValueError('Insufficient actual clearM7 tracks')
 col['selected_200_M7_x_nm']=[clear[((2*i+1)*len(clear))//400] for i in range(200)]
 col['M7_requested_word_cut']=200/len(clear)
 clear9=[x for x in col['tracks']['M9'] if x not in col['blocked']['M9']]
 if len(clear9)<146:raise ValueError('Insufficient actual clearM9 tracks')
 col['clear_M9_x_nm']=clear9
 col['selected_146_M9_x_nm']=[clear9[((2*i+1)*len(clear9))//292] for i in range(146)]
 col['M9_requested_word_cut']=146/len(clear9)
 col['blocked']={layer:sorted(v) for layer,v in col['blocked'].items()}
result=dict(schema='opentallas.qwen-dvm-actual-pg-audit.v1',qualified=False,adopted=False,odb=str(odb_path),odb_sha256=hashlib.sha256(odb_path.read_bytes()).hexdigest(),audit_tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),units_per_um=units,margin_nm=margin,counts=counts,columns=columns,
 source_fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.glob('*.json')},
 open=['Actual candidate head/leaf ports and native clock capture/launch not placed','Wholegraph signal cuts and clocks not reserved','Expanded column1473.12um height requires whole-die overlap/incident hop proof','Actual pin access/DRC and complete TT/FF signoff remain mandatory'],
 interpretation='Continuous vertical parent track clearance against actual placed PG wires and expanded via routing boxes only; not a grant')
output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(columns=len(columns),counts=counts,available_min={layer:min(c['available_requested_tracks'][layer] for c in columns.values()) for layer in ('M7','M9')},output=str(output))))
