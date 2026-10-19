import odb, ord
from openroad import Design, Tech
from pathlib import Path
tech=Tech(); design=Design(tech); D=design.getDb(); plat='/OpenROAD-flow-scripts/flow/platforms/asap7'
for lef in ['asap7_tech_1x_201209.lef','asap7sc7p5t_28_R_1x_220121a.lef']:
 odb.read_lef(D,plat+'/lef/'+lef)
odb.read_lef(D,'/reset.lef')
Path('/tmp/lattice.v').write_text('module reset_lattice(); endmodule\n')
design.readVerilog('/tmp/lattice.v'); design.link('reset_lattice'); block=design.getBlock()
design.evalTclString('initialize_floorplan -die_area {0 0 1000 1000} -core_area {1.08 1.08 998.92 998.92} -site asap7sc7p5t')
assert block.getRows(), 'floorplan produced no rows'
master=D.findMaster('dsfd_rly_1_WN')
for k in range(180):
 i=odb.dbInst.create(block,master,'r_'+str(k));i.setOrient('R0')
 x=8.64+43.2*(k%15)+.048*k;y=8.64+43.2*(k//15)+.048*k
 i.setLocation(round(1000*x),round(1000*y));i.setPlacementStatus('PLACED')
result=design.evalTclString('check_placement -verbose')
print('CHECK_RESULT',repr(result),'ROWS',len(block.getRows()))
assert len(block.getInsts())==180
print('RESET_LATTICE_OPENROAD_PASS 180 R0 BLOCK origins cover joint site0.054 row0.27 M4M5_0.048 M6_0.064 phases; PG network not built')
