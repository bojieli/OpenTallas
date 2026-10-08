import odb,json,hashlib,collections,pathlib
path=pathlib.Path('/input/3_2_place_iop.odb')
db=odb.dbDatabase.create();odb.read_db(db,str(path))
rows=[]
for bt in db.getChip().getBlock().getBTerms():
 pins=list(bt.getBPins());boxes=[box for pin in pins for box in pin.getBoxes()]
 rows.append({'name':bt.getName(),'sig_type':bt.getSigType(),'io_type':bt.getIoType(),'bpins':len(pins),'boxes':len(boxes)})
rows.sort(key=lambda x:x['name'])
summary={}
for sig in sorted({x['sig_type'] for x in rows}):
 subset=[x for x in rows if x['sig_type']==sig]
 summary[sig]={'bterms':len(subset),'bpins':sum(x['bpins'] for x in subset),'boxes':sum(x['boxes'] for x in subset)}
print('PIN_CLASSIFICATION_JSON '+json.dumps({'odb_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'summary':summary,'total_bterms':len(rows),'total_boxes':sum(x['boxes'] for x in rows),'bterms':rows}))
