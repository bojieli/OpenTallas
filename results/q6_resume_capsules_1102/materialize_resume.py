from pathlib import Path
import json,hashlib,shutil,sys,re
root=Path('/srv/opentallas-scratch2/claude/codex-q6-resume-prep-0230');sys.path.insert(0,str(root/'flow_source/tools/autopilot'))
import kit_resume as KR
import autopilot as AP
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
records={}
for leaf,oldname in [('recip','recip_c138_place1'),('zh','zh_place1')]:
 old=Path('/srv/opentallas-scratch2/claude/codex-pickup-kv')/oldname;s=root/'source'/leaf;c=root/'candidate'/leaf
 if not c.exists():shutil.copytree(s,c,ignore=lambda path,names: {'run'} if Path(path)==s else set())
 shutil.copyfile(root/('geometry_'+leaf)/'io.tcl',c/'io.tcl')
 proposed=json.loads((root/('geometry_'+leaf)/'pins.json').read_text())
 if proposed!=json.loads((s/'pins.json').read_text()):shutil.copyfile(root/('geometry_'+leaf)/'pins.json',c/'pins.json')
 KR.write_inputs(str(s));KR.write_inputs(str(c))
 om=KR.manifest(str(s),runner=str(s/'run_kit_kv.sh'));nm=KR.manifest(str(c),runner=str(c/'run_kit_kv.sh'));decision=KR.decide(nm,om)
 rtl={str(p.relative_to(s)):sha(p) for p in sorted((s/'rtl').rglob('*')) if p.is_file()}
 assert rtl and all(sha(c/n)==h==sha(old/n) for n,h in rtl.items())
 sdc={p.name:sha(p) for p in s.glob('*.sdc')};assert sdc and all(sha(c/n)==h==sha(old/n) for n,h in sdc.items())
 b=s/om['checkpoint']['base'];synth={n:sha(b/n) for n in KR.STEP_OUT['synth']};assert all(sha(old/om['checkpoint']['base']/n)==h for n,h in synth.items())
 missing=[];work_paths=sorted(set(re.findall(r'/work/([^\s\"\'()]+)',(c/'config.mk').read_text())))
 for p in work_paths:
  if '$' not in p and not p.startswith('run/') and not (c/p).exists():missing.append(p)
 runtime_generated=[]
 for name in missing:
  assert name=='adder_map_dontuse.v' and (c/'adder_map_dontuse.py').is_file() and 'adder_map_dontuse.py gen' in (c/'run_kit_kv.sh').read_text(),missing
  runtime_generated.append(dict(path=name,producer='unchanged run_kit_kv.sh -> adder_map_dontuse.py gen using immutable ORFS image platform files',producer_sha256=sha(c/'adder_map_dontuse.py'),historical_generated_bytes='absent in original; not fabricated',image=nm['image']))
 rec=dict(original=str(old),source_copy=str(s),candidate=str(c),flow_source_commit='b5bdd2126',source_rtl=rtl,sdc=sdc,synth=synth,source_and_sdc_identical=True,original_provenance_preserved=True,config_identical=sha(s/'config.mk')==sha(c/'config.mk'),config_work_paths=work_paths,runtime_generated_prerequisites=runtime_generated,changed_inputs=decision['changed'],normal_decision=decision,no_cad_dispatched=True,apply_performed=False)
 if decision['decision']=='resume':
  rec['apply']=KR.apply(str(c),str(s),decision,dict(kit=str(s),host=om['host'],same_host=True,checkpoint=om['checkpoint']))
  rec['verify']=KR.verify(str(c),str(s));assert not rec['verify'];rec['apply_performed']=True
 (root/(leaf+'_source_manifest.json')).write_text(json.dumps(om,indent=1)+'\n');(root/(leaf+'_candidate_manifest.json')).write_text(json.dumps(nm,indent=1)+'\n');(root/(leaf+'_resume_record.json')).write_text(json.dumps(rec,indent=2)+'\n')
 records[leaf]=rec
bundle=AP.stage_admission_tools(source_chain=root/'flow_source/tools/autopilot/signoff_chain.py',source_tools=root/'flow_source/tools/die_plan',root=root/'admission_tools')
assert Path(bundle['dir'],'die_plan/clock_family.tcl').is_file()
(root/'ADMISSION_BUNDLE.json').write_text(json.dumps(bundle,indent=2)+'\n')
print(json.dumps({n:{'normal_decision':r['normal_decision'],'candidate':r['candidate'],'source_and_sdc_identical':r['source_and_sdc_identical']} for n,r in records.items()},indent=2))
