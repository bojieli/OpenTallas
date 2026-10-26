import odb
from pathlib import Path
x=odb.dbDatabase.create();odb.read_lef(x,'/work/tiny.lef')
p=Path('/work/source.def').read_text().replace('+ FIXED M2','+ ROUTED M2').replace('+ FIXED M1 200','+ ROUTED M1 200')
Path('/work/source_routed_control.def').write_text(p)
odb.read_def(x.getTech(),'/work/source_routed_control.def')
b=x.getChip().getBlock();n=b.findNet('clk');w=n.getWire()
raw=lambda:[(w.getOpcode(i),w.getData(i)) for i in range(w.length())]
a=raw();print('HAS_NET_SETWIRETYPE',hasattr(n,'setWireType'),'HAS_WIRE_SETWIRETYPE',hasattr(w,'setWireType'))
if hasattr(n,'setWireType'):
 print('BEFORE',n.getWireType());n.setWireType('FIXED');print('AFTER',n.getWireType());print('OPCODES_IDENTICAL',a==raw())
odb.write_def(b,'/work/source_status_after.def')
print(Path('/work/source_status_after.def').read_text())
