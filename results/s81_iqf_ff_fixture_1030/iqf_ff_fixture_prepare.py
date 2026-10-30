from pathlib import Path
import json,shutil,importlib.util,subprocess
r=Path('/srv/opentallas-scratch2/claude/codex-s81types-1030/iqf_current_bind');f=r/'ff_fixture';f.mkdir(exist_ok=True)
old=json.load(open(r/'iqf_ft0_targets_legal.json'))['targets'];names=[x['name'] for x in old if 'x2' in x['master']];assert len(names)==434
new=json.load(open(r/'src/physical/die_plan/s81/iqf_reset_1030/ft0_full_stage.json'));rows={x['name']:x for x in new['slots']['ft0']['targets']};assert all(rows[n]['master']=='DFFHQNx1_ASAP7_75t_R' for n in names)
spec=importlib.util.spec_from_file_location('fixture_ft',r/'ft_full_stage_reviewed328.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
for mode in ['default','preserve']:
 k=f/mode
 if not k.exists():subprocess.run(['cp','--reflink=auto','-a',str(r/'gen_endpoint/iqf__t1'),str(k)],check=True)
 if mode=='preserve':M.install_family_preservation(new,k)
 t=['# Snapshot exact actual native434masters and D-pin buffer drivers.','set fixture_b [ord::get_db_block]','set fixture_f [open $::env(RESULTS_DIR)/fixture434_postresize.tsv w]']
 for n in names:
  t +=[f'set fixture_i [$fixture_b findInst {{{n}}}]','if {$fixture_i eq "NULL"} {error "Missing native target"}','set fixture_d [$fixture_i findITerm D]','if {$fixture_d eq "NULL"} {error "Missing actual D pin"}','set fixture_driver {}','set fixture_dm {}','foreach fixture_p [[$fixture_d getNet] getITerms] {if {[$fixture_p getIoType] eq "OUTPUT"} {set fixture_driver [[ $fixture_p getInst] getName];set fixture_dm [[[$fixture_p getInst] getMaster] getName]}}','puts $fixture_f "[$fixture_i getName]\\t[[$fixture_i getMaster] getName]\\t$fixture_driver\\t$fixture_dm"']
 t +=['close $fixture_f']
 snap='\n'.join(t)+'\n';(k/'fixture_snapshot.tcl').write_text(snap)
 force='source /work/fixture_snapshot.tcl\nfile rename -force $::env(RESULTS_DIR)/fixture434_postresize.tsv $::env(RESULTS_DIR)/fixture434_preforced.tsv\nputs "FIXTURE_FORCE_LAWFUL_DPIN_BUFFER_REPAIR max_wire_length50"\nestimate_parasitics -placement\nrepair_design -max_wire_length 50 -verbose\nsource /work/fixture_snapshot.tcl\n'
 (k/'fixture_force_repair.tcl').write_text(force)
 (k/'config.mk').write_text((k/'config.mk').read_text()+'\nexport POST_RESIZE_TCL = /work/fixture_force_repair.tcl\n')
 (k/'fixture434_names.json').write_text(json.dumps(names,indent=1)+'\n')
(f/'README.txt').write_text('ONE authorized matched native fixture, modes default/preserve. Same nativeG1, complete FT0 packet; approved source d274+328+c05502f. Actual nativeGPL then RESIZE including force-lawful 50um wire repair. No GRT/DPL/route/adoption. Default must demonstrate native FF sizing opportunity or nonvacuous requirement stays held. 434 prior x2 stage1 targets now actual fresh x1. Whole-family exclusions only in preserve physical process; buffer repair remains allowed.\n')
print('preparedmatchednativefixture434,2modes')
