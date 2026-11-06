"""Negative control only: reconnect one cold typed filler pin to a signal net."""
import json,sys
from pathlib import Path
import odb
src,dst,record=map(Path,sys.argv[1:4]);assert not dst.exists()
db=odb.dbDatabase.create();odb.read_db(db,str(src));block=db.getChip().getBlock()
for inst in block.getInsts():
 if not inst.getMaster().isFiller():continue
 for pin in inst.getITerms():
  old=pin.getNet()
  if old is None or str(old.getSigType()) not in ('POWER','GROUND'):continue
  create=getattr(odb.dbNet,'create',None) or getattr(odb,'dbNet_create',None)
  net=create(block,'__NEGATIVE_FILLER_SIGNAL');net.setSigType('SIGNAL');pin.connect(net)
  data={'negative_control':True,'filler':inst.getName(),'master':inst.getMaster().getName(),'pin':pin.getMTerm().getName(),'new_net':net.getName(),'new_sig_type':str(net.getSigType())}
  assert data['new_sig_type']=='SIGNAL';odb.write_db(db,str(dst));record.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data));raise SystemExit(0)
raise RuntimeError('no PG-connected typed filler for negative control')
