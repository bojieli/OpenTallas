import odb
x=odb.dbDatabase.create();odb.read_lef(x,"/work/tiny.lef");odb.read_def(x.getTech(),"/work/source_routed_control.def");odb.write_db(x,"/work/source_routed_control.odb")
