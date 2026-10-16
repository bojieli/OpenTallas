#!/usr/bin/env python3
"""Read actual snapshot LEFs; prepare isolated four-PHY PG fixture. No ODB inputs."""
import json,re,shutil,sys
from pathlib import Path
repo,case,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(repo/'tools'))
from phy_pg.hbm_assumed_pg import add_hbm_pg
out.mkdir(parents=True,exist_ok=True)
text=(case/'elements.historical-original.lef.txt').read_text()
target=re.search(r'(?ms)^MACRO qkd_hbm3e_phy_pc\n.*?^END qkd_hbm3e_phy_pc\s*$',text)[0]
source=re.search(r'(?ms)^MACRO ot_hbm3e_phy\n.*?^END ot_hbm3e_phy\s*$',(case/'phy_ew.lef').read_text())[0]
candidate,receipt=add_hbm_pg(target,source)
header='VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n'
(out/'hbm.lef').write_text(header+candidate+'\nEND LIBRARY\n')
(out/'hbm.original.lef.txt').write_text(header+target+'\nEND LIBRARY\n')
(out/'hbm.access.json').write_text(json.dumps(receipt,indent=2)+'\n')
(out/'fixture.v').write_text('module fixture();\n'+''.join('qkd_hbm3e_phy_pc '+n+'();\n' for n in ['phy_WS','phy_WN','phy_ES','phy_EN'])+'endmodule\n')
for file in ['fixture.tcl','run.sh']:shutil.copyfile(Path(__file__).with_name(file),out/file)
shutil.copyfile(repo/'tools/phy_pg/fixture/export_geometry.py',out/'export_geometry.py')
shutil.copyfile(repo/'tools/phy_pg/verify_geometry.py',out/'verify_geometry.py')

shutil.copyfile(repo/'tools/phy_pg/hbm_pg_interface.tcl',out/'hbm_pg_interface.tcl')
