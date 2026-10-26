import odb
x=odb.dbDatabase.create();odb.read_db(x,"/work/replayed.odb");b=x.getChip().getBlock();odb.dbWire.destroy(b.findNet("clk").getWire());b.findNet("VDD").destroySWires();odb.write_db(x,"/work/metal_free.odb")
