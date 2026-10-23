from pathlib import Path
import re,shutil
O=Path('/srv/opentallas-scratch/claude/codex-hbm-su-fan32-0400-1023');old=Path('/srv/opentallas-scratch/claude/ref_gate/hbm_su_pgslice_lg_ft_d4g-20261023-025308')
(O/'work').mkdir(exist_ok=True)
s=(old/'routes/gate/work/orfs/config.mk').read_text()
for x in sorted(set(re.findall(r'/src/[^\s]+',s))):
 src=old/'src'/x.removeprefix('/src/'); dst=O/'src'/x.removeprefix('/src/')
 if not src.is_file():continue
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
for part in ['tools/ref_tile','tools/tt_views','physical/common_flow']:
 src=old/'src'/part
 if src.exists():shutil.copytree(src,O/'src'/part,dirs_exist_ok=True)
s=s.replace('ot_hbm_su_static_pgslice_rgf_lp__ftsw3','ot_hbm_su_static_pgslice_rgf_lp_n32').replace('/top/lp/ft/ot_hbm_su_static_pgslice_rgf_lp_n32.sv','/top/lp/ot_hbm_su_static_pgslice_rgf_lp_n32.sv')
s+='\nexport VERILOG_FILES += /src/rtl/common/landed_parent/ot_pl_land_n32.sv /src/rtl/common/landed_parent/ot_pl_land_split.sv /src/rtl/common/landed_parent/ot_pl_land_rst_copy.sv\nexport NUM_CORES = 8\n'
(O/'work/config.mk').write_text(s)
for f in ['ot_pl_land_n32.sv','ot_pl_land_split.sv','ot_pl_land_rst_copy.sv']:
 src=O/f if (O/f).exists() else O/'rtl/common/landed_parent'/f
 shutil.copy2(src,O/'src/rtl/common/landed_parent'/f)
shutil.copy2(O/'ot_hbm_su_static_pgslice_rgf_lp_n32.sv',O/'src/rtl/hbm_accel/generic/adapters/static_su/top/lp/ot_hbm_su_static_pgslice_rgf_lp_n32.sv')
shutil.copy2(old/'routes/gate/work/orfs/constraint.sdc',O/'work/constraint.sdc')
(O/'work/audit.py').write_text("""import glob,subprocess,json
libs=glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*')+glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*FF*.lib*')+glob.glob('/src/physical/ref_tile/hbm_su_static*/*/*/*_tt.lib')+glob.glob('/src/physical/ref_tile/hbm_su_static*/*/*/*_ff.lib')
n=glob.glob('/work/results/asap7/*/base/1_2_yosys.v');assert len(n)==1,n
a=['python3','/src/tools/ref_tile/native_census.py','--netlist',n[0],'--top','ot_hbm_su_static_pgslice_rgf_lp_n32','--out','/work/native_census.json']
for p in sorted(set(libs)):a+=['--liberty',p]
r=subprocess.run(a,stdout=open('/work/native_full.log','w'),stderr=subprocess.STDOUT)
d=json.load(open('/work/native_census.json'));print(d.get('status'),d.get('max_dynamic_loads'),len(d.get('violations',[])))
raise SystemExit(r.returncode)
""")
print('SETUP_READY')
