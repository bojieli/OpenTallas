from pathlib import Path
import shutil,json,sys
r=Path(__file__).resolve().parents[3];d=Path(__file__).resolve().parent;b=Path(sys.argv[1]);k=Path(sys.argv[2]);assert not k.exists();k.mkdir();(k/'.keep').touch()
js={'freeze.json','core.json','pins.json','plan_pins.json','face_shell.json','sdc_lint.json','boundary_guard_context.json','reset_contract.json','clock_density_contract.json','native_clock_port_contract.json'}
for p in b.iterdir():
 if p.is_file() and (p.suffix in {'.py','.sh','.tcl','.mk','.sdc','.env'} or p.name in js or p.name=='ft_stations.txt') and not p.name.endswith('.py.routed'):shutil.copy2(p,k/p.name)
for n in ['rtl','macros','reset_contract']:
 if (b/n).exists():shutil.copytree(b/n,k/n)
shutil.copy2(r/'rtl/hdc/v41x/ot_dsrom_divc.sv',k/'rtl/ot_dsrom_divc.sv')
for n in ['orfs_hold_mm.py','orfs_hold_mm.tcl']:shutil.copy2(d/n,k/n)
p=k/'config.mk';p.write_text(p.read_text().replace('OT_HOLD_REPAIR_SCOPE = reg2reg','OT_HOLD_REPAIR_SCOPE = nonport'))
(k/'FORM_CANDIDATE.json').write_text(json.dumps(dict(owner='CODEX-HBM-0615',form='n4_vCF2',base='vCF1',kind='NEW_RTL_REBUILD_NOT_ECO',changes=['exact128entryradix16dstep lookup,no cycles','nonportMM1369repair:excludeinputsONLY'],pin_cycles=0,qualification='DO_NOT_COUNT pending PLACE/route/proof/parentadoption'),indent=1)+'\n')
print(k)
