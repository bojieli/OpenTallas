#!/usr/bin/env python3
import sys,glob,subprocess
from pathlib import Path
h,top=sys.argv[1:3];net=sys.argv[3]if len(sys.argv)>3 else'1_2_yosys.v';libs=glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*');cmd='\n'.join('read_liberty -lib -ignore_miss_func '+p for p in sorted(libs))+'\n'
assert len(libs)>=5,libs
cmd+=f'read_verilog /in/{net}\nhierarchy -top {top}\nsetattr -mod -unset keep_hierarchy\nsetattr -unset keep_hierarchy\nflatten\nwrite_json /out/flat_{h}.json\n'
p=Path('/out')/f'flat_{h}.ys';p.write_text(cmd)
with(Path('/out')/f'yosys_flat_{h}.log').open('w')as f:subprocess.run(['yosys','-s',str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
