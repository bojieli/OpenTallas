#!/usr/bin/env python3
"""Generate the source-defined L2 compact trial with a central movable-logic region."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[4]
a=argparse.ArgumentParser();a.add_argument('--plan',required=True);a.add_argument('--out',required=True);a.add_argument('--suffix',default='compact_region');a=a.parse_args()
g=R/'physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py'
subprocess.run([sys.executable,str(g),'--module','dsdv_gunit_l2','--out',a.out,'--suffix',a.suffix,'--master-slice',str(H),'--plan',a.plan,'--trial'],check=True)
k=Path(a.out)/('dsdv_gunit_l2_'+a.suffix)
shutil.copyfile(H/'logic_region.tcl',k/'l2_logic_region.tcl')
f=k/'face_flops.tcl';f.write_text(f.read_text()+'\nsource /work/l2_logic_region.tcl\n')
shutil.copyfile(R/'physical/die_plan/s81/inputs/core_pins/dsdv_gunit_l2_compact_1028.json',k/'plan_pins.json')
sp=importlib.util.spec_from_file_location('l2_generator',g);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
f=k/'freeze.json';s=json.load(open(f));s['placement_region']=dict(rect_um=[86.4,12.96,172.8,30.24],owner='source L2 compaction event',hook_sha256=hashlib.sha256((k/'l2_logic_region.tcl').read_bytes()).hexdigest());s['kit_hash']=m.kit_hash(k);f.write_text(json.dumps(s,indent=1)+'\n');print(json.dumps(dict(kit=str(k),kit_hash=s['kit_hash'],placement_region=s['placement_region'])))
