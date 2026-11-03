from pathlib import Path
import sys
p=Path(sys.argv[1])
for name,old,new in [('global_place.tcl','load_design 3_2_place_iop.odb 2_floorplan.sdc','load_design sc_place_corrected.odb 3_place.sdc'),('detail_place.tcl','load_design 3_4_place_resized.odb 2_floorplan.sdc','load_design 3_3_place_gp.odb 3_place.sdc')]:
 f=p/name;s=f.read_text()
 if s.count(old)!=1:raise ValueError((name,'unexpectednativeinputanchor'))
 f.write_text(s.replace(old,new,1));print('SC_NATIVE_STAGE_INPUT',name,old,'->',new)
