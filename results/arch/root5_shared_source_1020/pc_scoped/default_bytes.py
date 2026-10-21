"""Compare emitted SDC for real pre-existing non-dual source modes on fleet."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools/ref_tile'))
import clock_entry_constraints as C
import test_gray_fifo_cdc_constraints as T
import test_async_gray_fifo_constraints as A
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
records={}
for name,cls,make in [('fifo',T.Fixture,T.spec),('extended',T.ExtFixture,T.ext_spec),('events',T.EvFixture,T.ev_spec)]:
 fixture=cls();fixture.setUp()
 try:
  s=C.generate(make(),fixture.root);(out/(name+'.sdc')).write_text(s)
  records[name]=dict(sha256=hashlib.sha256(s.encode()).hexdigest(),bytes=len(s.encode()))
 finally:fixture.tearDown()
s=C.generate(A.spec(),A.ROOT);(out/'ordinary.sdc').write_text(s)
records['ordinary']=dict(sha256=hashlib.sha256(s.encode()).hexdigest(),bytes=len(s.encode()))
(out/'hashes.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
