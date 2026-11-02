from pathlib import Path
import sys,json,re,hashlib,importlib.util
k=Path(sys.argv[1]);sp=importlib.util.spec_from_file_location('kit_modes',k/'kit_modes.py');km=importlib.util.module_from_spec(sp);sp.loader.exec_module(km)
cfg=(k/'config.mk').read_text();v=km.mk_vars(cfg);cfgrefs=sorted(set(re.findall(r'/work/[A-Za-z0-9_./-]+',cfg)))
missing=[x for x in cfgrefs if not (k/x.removeprefix('/work/')).exists()];assert not missing,missing
roots=[Path(x.removeprefix('/work/')).name for x in cfgrefs if x.endswith(('.tcl','.sdc'))]
roots += ['run_kit.sh','kit_modes.py','kit_modes_eco.tcl','orfs_hold_mm.py','orfs_hold_mm.tcl','sdc_lint.py','rtl_lint.py','face_guard_core.py','legacy_gate.py']
manual={'tap_balance.tcl':['clock_family.tcl'],'orfs_hold_mm.tcl':['macro_cts_cluster.tcl','constraint.sdc','vclk_ff.sdc'],'setRC_rcx.tcl':[]}
seen=set();edges=[];todo=list(roots)
while todo:
 name=todo.pop()
 if name in seen:continue
 seen.add(name);p=k/name;assert p.is_file(),name
 if p.suffix not in ['.tcl','.sdc']:continue
 text=p.read_text();deps=sorted(set(km.SOURCE_RE.findall(text)+manual.get(name,[])))
 for dep in deps:
  assert (k/dep).is_file(),(name,dep)
  edges.append({'from':name,'to':dep});todo.append(dep)
i=json.loads((k/'source_proof_identity.json').read_text());d=json.loads((k/'source_proof/lec.json').read_text());assert d['verdict']=='EQUIVALENT' and d['counts']['differs']==d['counts']['undecided']==0
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for f,want in i['inputs_sha256'].items():assert h(k/f)==want,f
odb='run/results/asap7/kl_dsdv_bksel_c_pipe_ab_r1_1131/base/3_place.odb';assert h(k/odb)==i['corrected_odb_sha256'];assert not list((k/odb).parent.glob('4_*'))
o={'verdict':'PASS','scope':'prepared input closure and exact source identity; no CTS launched','config_work_references':[{ 'path':x,'kind':'directory' if (k/x.removeprefix('/work/')).is_dir() else 'file','sha256':None if (k/x.removeprefix('/work/')).is_dir() else h(k/x.removeprefix('/work/'))} for x in cfgrefs], 'hook_edges':edges,'required_runtime_files_sha256':{n:h(k/n) for n in sorted(seen)},'inactive_optional_sources':{'grt_maxwire.tcl':'OT_MAXWIRE_UM absent from frozen config and no Docker host env passed','vclk_measured_hold.tcl':'OT_MM_MEASURED_HOLD absent; bound-FF202.5 contract retained','frozen_clock_rc.tcl':'OT_MM_FROZEN_CLOCK_SPEFS absent; no inherited Docker env','tap_balance_external_fallback':'local clock_family.tcl present and hash pinned','macro_cts_external_fallback':'local macro_cts_cluster.tcl present and hash pinned'},'source_inputs_verified':len(i['inputs_sha256']),'official_eq_sha256':i['receipt_sha256'],'reviewed_3_place_sha256':h(k/odb),'normal_consumer':'generated full run_kit.sh; supported completed standalone proof reuse API pending tool-owner response'}
(k/'prepared_input_closure.json').write_text(json.dumps(o,indent=2)+'\n');print('PREPARED_INPUT_HOOK_CLOSURE_PASS',len(cfgrefs),'configrefs',len(seen),'runtimefiles',len(edges),'hookedges',len(i['inputs_sha256']),'proofinputs');print(json.dumps(edges,indent=2))
