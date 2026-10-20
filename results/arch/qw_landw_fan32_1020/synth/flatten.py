import glob,subprocess,os
from pathlib import Path
libs=glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*')
assert len(libs)>=5
s=''.join('read_liberty -lib -ignore_miss_func '+p+'\n'for p in sorted(libs))
top=os.environ.get('OT_NATIVE_TOP','qfd_landh0d8f_116_EW_46x46')
s+='read_verilog /out/1_2_yosys.raw.v\nhierarchy -top '+top+'\nsetattr -mod -unset keep_hierarchy\nsetattr -unset keep_hierarchy\nflatten\nwrite_json /out/flat.json\n'
Path('/out/flat.ys').write_text(s)
subprocess.run(['yosys','-s','/out/flat.ys'],check=True)
