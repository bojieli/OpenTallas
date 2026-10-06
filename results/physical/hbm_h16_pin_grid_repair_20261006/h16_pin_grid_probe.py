import odb,json,hashlib,collections
from pathlib import Path
D=odb.dbDatabase.create();odb.read_db(D,'/checkpoint/4_cts.odb');b=D.getChip().getBlock();ly=D.getTech().findLayer('M4');grid=list(b.findTrackGrid(ly).getGridY());rows=[]
for i in b.getInsts():
 if i.getMaster().getName()!='ot_attn_hgrp_m6h1':continue
 bad=[];allpin=0
 for t in i.getITerms():
  if t.getSigType() in ('POWER','GROUND'):continue
  allpin+=1
  boxes=t.getGeometries() if hasattr(t,'getGeometries') else []
  # Actual R0 transform of retained master geometry, not guessed outline.
  x,y=i.getOrigin()
  if str(i.getOrient())!='R0':raise RuntimeError('Unexpected orientation '+str(i.getOrient()))
  for mp in t.getMTerm().getMPins():
   for box in mp.getGeometry():
    if box.getTechLayer()!=ly:continue
    lo,hi=y+box.yMin(),y+box.yMax()
    hits=[q for q in grid if lo<=q<=hi]
    if not hits:bad.append(t.getMTerm().getName())
 row={'inst':i.getName(),'origin_DBU':list(i.getOrigin()),'orientation':str(i.getOrient()),'M4_signal_pins':allpin,'M4_pins_without_native_Y_track':bad}
 rows.append(row)
r={'ODB_sha256':hashlib.sha256(Path('/checkpoint/4_cts.odb').read_bytes()).hexdigest(),'DBU':b.getDbUnitsPerMicron(),'M4_track_start_DBU':grid[:4],'M4_track_pitch_DBU':grid[1]-grid[0],'macros':rows}
Path('/output/pin_grid.json').write_text(json.dumps(r,indent=2)+'\n');print([(x['origin_DBU'],len(x['M4_pins_without_native_Y_track'])) for x in rows])
