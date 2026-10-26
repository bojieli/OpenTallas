import odb
x=odb.dbDatabase.create();odb.read_db(x,'/work/final.odb')
b=x.getChip().getBlock();n=b.findNet('clk');assert n.getWire()
odb.dbWire.destroy(n.getWire());odb.write_db(x,'/work/mutant_missing_clock_wire.odb')
