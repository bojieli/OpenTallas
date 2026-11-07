from pathlib import Path
import shutil,json
b=Path('/tmp/codex-hbm-0615');base=b/'f512base_unpacked';k=b/'f512_vCF1';k.mkdir(exist_ok=True);(k/'.keep').touch();r=Path('/srv/opentallas-scratch/claude/codex-hbm-0615/src');h=r/'physical/die_plan/hbm_arch_cores';t=r/'tools/die_plan'
static={'freeze.json','face_shell.json','pins.json','plan_pins.json','core.json','boundary_guard_context.json','reset_contract.json','clock_density_contract.json','native_clock_port_contract.json','ft_stations.txt','variant.env'}
for p in base.iterdir():
 if p.is_file()and(p.suffix in ['.py','.sh','.tcl','.mk','.sdc','.env']or p.name in static):shutil.copy2(p,k/p.name)
for n in ['rtl','macros','reset_contract']:shutil.copytree(base/n,k/n,dirs_exist_ok=True)
# Current released generation/runtime helpers; no old gate outputs are copied.
for n in ['corners_hbm.tcl','run_kit_hbm.sh','face_guard_core.py','dump_placed.py','hold_cap.tcl','hold_gate.tcl','port_bind_core.py','internal_core_guard.py']:
 shutil.copy2(h/n,k/n)
for n in ['lec.py','lec_async.sh','selrange_gate.py','rtl_lint.py']:shutil.copy2(t/n,k/n)
# Exactly the normal-proven candidate; retain all native8-root clock contracts.
s=(b/'f512bench/new0.sv').read_text().replace('module f512_new0 (','module hnx_vms_bank_q0_faces__vecd4ae (',1);assert 'module hnx_vms_bank_q0_faces__vecd4ae ('in s
(k/'rtl/hnx_vms_bank_q0_faces__vecd4ae__fshell.sv').write_text(s);shutil.copy2(b/'f512bench/reset.sv',k/'rtl/ot_hbm_face_rst_relay.sv')
for n in ['input_relay_guide.tcl','input_relay_guide_release.tcl']:shutil.copy2(b/'f512cf1'/n,k/n)
with (k/'face_flops.tcl').open('a')as f:f.write('\nsource /work/input_relay_guide.tcl\n')
with (k/'face_flops_release.tcl').open('a')as f:f.write('\nsource /work/input_relay_guide_release.tcl\n')
with (k/'config.mk').open('a')as f:f.write('''\n# CODEX F512 vCF1: coherent+1 input hop, +1 delivered reset release, guide each relay into legal measured midpoint corridor.\nexport VERILOG_FILES += /work/rtl/ot_hbm_face_rst_relay.sv\noverride export OT_HOLD_REPAIR_SCOPE = reg2reg\n''')
(k/'max_fanout.tcl').write_text('set_max_fanout 8 [current_design]\nputs "F512 vCF1 max_fanout8"\n')
j=json.load(open(k/'face_shell.json'));st=json.load(open(b/'f512bench/pincycles.json'))['in_extra_stages'];j['in_extra_stages']=st;j['in_extra_stage_flops']=2059;j['latency']['reset_delay_cycles']=1;j['latency']['note']+='; CODEX coherent+1 input relays; delivered reset release+1, immediateassert unchanged';j['files'].append('ot_hbm_face_rst_relay.sv');(k/'face_shell.json').write_text(json.dumps(j,indent=1)+'\n')
shutil.copy2(b/'f512bench/pincycles.json',k/'PIN_CYCLES.json')
(k/'FORM_CANDIDATE.json').write_text(json.dumps(dict(owner='CODEX-HBM-0615',form='f512_vCF1',kind='NEW_REBUILD_NOT_ECO',base='intel1:hbm-form-timing-12/f512rp_eco/i3',changes=['2059 guidedinputrelays','one extra delivered resetrelease cycle','reg2reg holdscope','fanout64to8'],native_clock_contract='unchanged separate8roots+densitycommonalignment',qualification='DO_NOT_COUNT pending actualgates and parentcompiler+latencyadoption',geometry='actualpin/nativecapture guidepositions; worstleg280.113um inclguideextent; maxadded8umbin.15947',proof='m0 lockstep0diff/2564reads/412writes; exercised rowbit268 bypassmutant6516 mismatches; deadbit267mutant retainedFAIL'),indent=1)+'\n')
print('assembled',k,'files',len(list(k.rglob('*'))),'profile',json.load(open(k/'freeze.json')).get('source_profile'))
