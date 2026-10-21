import glob,subprocess
from pathlib import Path
libs=glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*')
assert len(libs)>=5
s=''.join('read_liberty -lib -ignore_miss_func '+p+'\n'for p in sorted(libs))
s+='read_verilog -lib /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v\nread_verilog /out/1_2_yosys.raw.v\nhierarchy -top ot_qfd_tt_ctlm_static_hr\nsetattr -mod -unset keep_hierarchy\nsetattr -unset keep_hierarchy\nflatten\nwrite_json /out/flat.json\n'
Path('/out/flat.ys').write_text(s)
subprocess.run(['yosys','-s','/out/flat.ys'],check=True)
