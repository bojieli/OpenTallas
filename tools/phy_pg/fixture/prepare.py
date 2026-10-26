#!/usr/bin/env python3
"""Usage: prepare.py REPOSITORY OUTPUT_DIR. Run fixture in pinned ORFS via ot-run."""
import json
import shutil
import sys
from pathlib import Path
root,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(root/'tools'))
from phy_pg.assumed_access import build
out.mkdir(parents=True,exist_ok=True)
for src,dst in [('physical/qwen_missing_phy/tp8_1013/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy.lef','serdes'),('physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy.lef','ucie')]:
 text=(root/src).read_text();candidate,receipt=build(text)
 (out/(dst+'.lef')).write_text(candidate);(out/(dst+'.original.lef.txt')).write_text(text)
 (out/(dst+'.access.json')).write_text(json.dumps(receipt,indent=2)+'\n')
for file in ['fixture.tcl','export_geometry.py','run.sh']:
 shutil.copyfile(Path(__file__).with_name(file),out/file)
shutil.copyfile(root/'tools/phy_pg/assumed_access.tcl',out/'assumed_access.tcl')
for file in ['pdn_bbox_obs.py','pdn_bbox_obs.tcl']:
 shutil.copyfile(root/'tools/qwen_kv_die/chain'/file,out/file)
(out/'assumed_phy_pg_access.json').write_text(json.dumps({'schema':'opentallas.assumed-phy-pg-case.v1','status':'ASSUMED_UNQUALIFIED'}))
shutil.copyfile(root/'tools/phy_pg/verify_geometry.py',out/'verify_geometry.py')
ns=['serdes_r0','ucie_mx','serdes_my','ucie_r180','serdes_mx','ucie_r0','serdes_r180','ucie_my']
ms=['ot_qfd_serdes_112g_x12_phy','ot_qkvd_ucie_x64_phy']*4
(out/'fixture.v').write_text('module fixture();\n'+''.join(f'{m} {n}();\n' for n,m in zip(ns,ms))+'endmodule\n')
