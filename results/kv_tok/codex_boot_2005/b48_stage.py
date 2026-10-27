from pathlib import Path
import shutil,re,json
base=Path('/srv/opentallas-scratch2/claude/tok-qk-b48/build3')
own=Path('/srv/opentallas-scratch2/claude/codex-kv-boot-2005')
wt=Path('/srv/opentallas-scratch2/claude/wt/codex-kv-boot-2005')
obj=own/'build/obj';obj.mkdir(parents=True,exist_ok=True)
for d in (base/'obj').iterdir():
 if d.is_dir():
  dest=obj/d.name
  if dest.exists():continue
  if d.name.startswith('Vkv3_pc') or d.name=='Vtb_kvslice__hier.dir': shutil.copytree(d,dest)
  elif d.name=='Vkv3_hub_Wi_part':shutil.copytree(Path('/srv/opentallas-scratch2/claude/tok-qk-b48/build/obj')/d.name,dest)
  else: dest.symlink_to(d,target_is_directory=True)
 elif d.name.endswith(('.f','_hier.mk')):shutil.copy2(d,obj/d.name)
# Existing fixed HOST lib is complete; its source args point at gate3 private ABI-correct HOST input.
a=obj/'Vkv3_hub_Wi_part__hierMkArgs.f'
shutil.copy2('/srv/opentallas-scratch2/claude/tok-qk-b48/build/obj/Vkv3_hub_Wi_part__hierMkArgs.f',a)
fixes={n:str(wt/'rtl/qwen_sys/static_kv_20261014'/n) for n in ['ot_qkd_static_kv_timing.sv','ot_qkd_static_ctrl_pc_emb.sv','qkd_ctrl_pc_nc.sv','qkd_ctrl_pc_host_static_core.sv','qkd_kvpc_sram_clones_1019.sv']}
libs=[]
for a in obj.glob('Vkv3_pc*__hierMkArgs.f'):
 lines=a.read_text().splitlines(); changes=[]
 for i,line in enumerate(lines):
  name=Path(line).name
  if name in fixes:lines[i]=fixes[name];changes.append(name)
 a.write_text('\n'.join(lines)+'\n');libs.append(a.name.removesuffix('__hierMkArgs.f'))
(own/'pc_libs.json').write_text(json.dumps(libs,indent=2)+'\n')
s=(obj/'Vtb_kvslice_hier.mk').read_text();s=re.sub(r'^VM_HIER_RUN_DIR := .*',f'VM_HIER_RUN_DIR := {own}/build',s,flags=re.M);(obj/'Vtb_kvslice_hier.mk').write_text(s)
# Functional native tb7 has exact 833ps domain and static host pacing, qualified by B33 run7.
import sys
sys.path.insert(0,str(wt/'tools/qwen_layerbench/kv_dieslice'))
from bind_tb_clocks import bind_clocks
s,names=bind_clocks((base/'top_s/qwen_kvsys_bound_top.sv').read_text(),(own/'native_tb.sv').read_text())
s=s.replace('wait (bo_sig[3] && dut.sys_SW.u_core.tx_up && dut.sys_SE.u_core.tx_up);','while (!(bo_sig[3] && dut.sys_SW.u_core.tx_up && dut.sys_SE.u_core.tx_up) && cyc_core < maxcyc) @(posedge ck_core);\n        if (cyc_core >= maxcyc) $fatal(1, "KVSLICE_BOOT FAIL no link before MAXCYC");')
(own/'tb_native_regions.sv').write_text(s)
(own/'clocks.json').write_text(json.dumps({'region_inputs':names,'clock':'ck_core','period_ps':833},indent=2)+'\n')
a=obj/'Vtb_kvslice__hierMkArgs.f';lines=a.read_text().splitlines()
for i,line in enumerate(lines):
 if line.endswith('/tb_kvslice.sv'):lines[i]=str(own/'tb_native_regions.sv')
 elif line.endswith('/qkd_hbm3e_phy_pc4_bench.sv'):lines[i]=str(wt/'tools/qwen_layerbench/kv_dieslice/qkd_hbm3e_phy_pc4_bench.sv')
a.write_text('\n'.join(lines)+'\n')
print('staged',len(libs),'PC libraries and',len(names),'region clocks')
