import glob,subprocess,json,re
from pathlib import Path
libs=[]
for path in re.findall(r'Liberty frontend: (\S+)',Path('/out/orfs_synth.log').read_text()):
 if '/platforms/asap7/lib/NLDM/' in path and '_RVT_TT_' in path and path not in libs:libs.append(path)
 if len(libs)==5:break
assert len(libs)==5 and all(Path(x).exists()for x in libs),libs
macros=['ot_sram_1r1w_64x512_m1_r2c2','ot_sram_1r1w_32x128_m1']
base='/src/physical/asap7_memory_macros/'
alllibs=libs+[base+x+'/'+x+'_tt.lib' for x in macros]
a=['python3','/src/results/rtl/qw_head_safe32_1020/native_synth/runtime/ref_tile/native_census.py','--netlist','/out/1_2_yosys.raw.v','--top','ot_qfd_tt_ctlm_static_hr_safe32_native32','--out','/out/native_census_current.json']
for l in alllibs:a+=['--liberty',l]
rc=subprocess.run(a).returncode
s=''.join('read_liberty -lib -ignore_miss_func '+l+'\n'for l in libs)
s+=''.join('read_verilog -lib '+base+x+'/'+x+'_bb.v\n'for x in macros)
s+='read_verilog /out/1_2_yosys.raw.v\nhierarchy -top ot_qfd_tt_ctlm_static_hr_safe32_native32\nsetattr -mod -unset keep_hierarchy\nsetattr -unset keep_hierarchy\nflatten\nwrite_json /out/flat.json\n'
Path('/out/flat.ys').write_text(s);subprocess.run(['yosys','-s','/out/flat.ys'],check=True)
raise SystemExit(rc)
