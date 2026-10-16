import odb,json
from pathlib import Path
for name in ['h7','f20_west']:
 db=odb.dbDatabase.create();odb.read_db(db,'/audit/'+name+'.odb');b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();t=db.getTech();out={'case':name,'units_per_um':u,'tracks':{},'pins':[]}
 for layer in ['M3','M4','M5']:
  g=b.findTrackGrid(t.findLayer(layer));out['tracks'][layer]={'X':[g.getGridPatternX(i) for i in range(g.getNumGridPatternsX())],'Y':[g.getGridPatternY(i) for i in range(g.getNumGridPatternsY())]}
 for bt in b.getBTerms():
  for bp in bt.getBPins():
   for bx in bp.getBoxes():
    ln=bx.getTechLayer().getName();r=[bx.xMin(),bx.yMin(),bx.xMax(),bx.yMax()];axis='Y' if ln=='M4' else 'X';c=(r[1]+r[3])/2 if axis=='Y' else (r[0]+r[2])/2
    patterns=out['tracks'].get(ln,{}).get(axis,[]);ok=any(0<=round((c-start)/step)<count and abs(c-start-round((c-start)/step)*step)<.01 for start,count,step in patterns)
    out['pins'].append({'name':bt.getName(),'layer':ln,'rect_dbu':r,'axis':axis,'centre_dbu':c,'on_actual_track':ok})
 print('GRID_READBACK_JSON '+json.dumps(out,separators=(',',':')))
