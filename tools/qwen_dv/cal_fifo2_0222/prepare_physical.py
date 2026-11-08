from pathlib import Path
import json,subprocess,os,hashlib,re
S=Path('/srv/opentallas-scratch2/claude/codex-qc-cal-fifo2-physical-0222')
ROOT=Path('/srv/opentallas-scratch2/claude/codex-qc-cal-fifo2-physical-0222-run1')
W=ROOT/'fifo2_form_a'
B=Path('/srv/opentallas-scratch2/claude/codex-qc-nl-native-0222-run7/bind')
A=S/'physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt.json'
P0=Path('/srv/opentallas-scratch2/claude/codex-qc-su1-physical-0222/tools/qwen_dv/su1_mem9_physical_0222/base_qc53v4s.json')
T='tt_ctlm'
assert (B/'bind_report.json').is_file(), 'collect successful strict bind first'
W.mkdir(parents=True,exist_ok=False)
d=json.loads(P0.read_text());t=d['partition_types'][T]
original=t['hard_cores'];removed=[];kept=[]
for hc in original:
 if re.fullmatch(r'u_bound\.u_core\.u_gi\.u_cal\.g_fifo\[[0-3]\]\.u_fifo',hc['inst']):removed.append(hc)
 else:kept.append(hc)
assert len(removed)==4 and all(x['module']=='ot_sram_1r1w_64x512_m1_r2c2' for x in removed)
t['hard_cores']=kept
assert len(kept)==len(original)-4
p=W/'plan_fifo2.json';p.write_text(json.dumps(d,indent=1)+'\n')
for f in (S/'physical/die_plan/qwen_compute/plan_of_record').iterdir():
 dest=W/f.name
 if not dest.exists():dest.symlink_to(f)
(W/'FORM_MODEL.json').write_text(json.dumps({'source':'88a99cfa19d','only_changed_type':T,'removed_fifo_hardcores':removed,'kept_hardcores':kept,'data_cycles_delta':0,'pin_cycles_delta':0,'ff_storage_bits':4096,'registered_read_bits':2048,'total_ff_bits':6144,'control':'32 local16bit groups per FIFO, bounded inverter hierarchy; actual mapped fanout/placement required before CTS','proof':'792x512bit reads0diff; wrongrow792 and extraedge233 mutants; oneedge RbeforeW/CEhold/unreset','scope':'private GEN then reviewed SYNTH/PLACE form; no adoption'},indent=2)+'\n')
os.environ['OT_CONS_KIT']='1';os.chdir(S)
def run(label,args):
 with (W/(label+'.log')).open('w') as out:r=subprocess.run(['python3','-I','-B',*map(str,args)],stdout=out,stderr=subprocess.STDOUT)
 print(label,'RC',r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
run('kit_rtl',[S/'tools/die_plan/bind.py','kit-rtl',p,'--out',B,'--asbuilt',A,'--type',T,'--kit',W/'rtl'])
f=W/'rtl/kit_rtl.f';lines=f.read_text().splitlines()
old='qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1.sv'
variant=S/'rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1_fifo2.sv'
helper=S/'rtl/physical/ot_qc_cal_fifo2_512.sv'
matches=[x for x in lines if Path(x).name==old];assert len(matches)==1,matches
lines=[str(variant) if x==matches[0] else x for x in lines]+[str(helper)]
assert all(Path(x).name!=old for x in lines)
f.write_text('\n'.join(lines)+'\n')
(W/'SOURCE_FORM.json').write_text(json.dumps({'source_commit':'88a99cfa19d','old_file':matches[0],'alternate':str(variant),'helper':str(helper),'sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in [variant,helper]},'four_bounded_fifo_only':True,'pin_cycles':0},indent=2)+'\n')
run('prov',[S/'tools/autopilot/prov_view.py','make','--plan',p,'--type',T,'--out',W/'prov','--src',S,'--rtl',W/'rtl'])
ov=[json.loads(x[10:])['overlay_plan'] for x in (W/'prov.log').read_text().splitlines() if x.startswith('PROV_JSON ')][-1]
run('topology',[S/'tools/die_plan/kit_topology.py','prepare-stations',ov,T,W/'rtl','--native-plan',p,'--asbuilt',A])
run('gen',[S/'tools/die_plan/gen.py','phys',ov,'--out',W/'gen','--types',T,'--rtl-root',S,'--kit-rtl',T+'='+str(f),'--cland-pinslot','all','--hold-ff-margin','0','--clock-landing',S/'physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar.json'])
K=W/'gen'/T
(K/'DO_NOT_COUNT').write_text('Private calendar FIFO2 candidate; no CTS/route before actual mapped control/fanout and geometry review; no adoption.\n')
print('FIFO2_GEN_PASS',K,flush=True)
