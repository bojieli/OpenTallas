from pathlib import Path
import json,re,collections,hashlib,gzip,shutil
root=Path('/srv/opentallas-scratch/claude/codex-hroot-address-1021');a=root/'hroot-address-map-r2-1021';b=root/'hroot-address-map-baseline-1021';out=root/'sealed_packet';out.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def warnings(p):return [l for l in (p/'map.log').read_text().splitlines() if l.startswith('Warning:')]
def norm(s):return re.sub(r'\$\d+', '$N',re.sub(r'qkd_host_native_engine\.sv:\d+','qkd_host_native_engine.sv:LINE',s))
wa,wb=warnings(a),warnings(b);ca,cb=collections.Counter(map(norm,wa)),collections.Counter(map(norm,wb));extra=list((ca-cb).elements());missing=list((cb-ca).elements());assert not missing,missing;assert len(extra)==32 and all('Replacing memory' in x and 'af_add32' in x for x in extra),extra
sa=(a/'original.v').read_text();sb=(b/'original.v').read_text();targets=['.w2','ob','oh','g_qp.l'];absence={}
for key in targets:
 pat=re.compile(re.escape(key) if key.startswith('.') else r'(?<![A-Za-z0-9_.$])'+re.escape(key)+r'(?![A-Za-z0-9_.$])');absence[key]={'candidate_occurrences':len(pat.findall(sa)),'baseline_occurrences':len(pat.findall(sb))};assert absence[key]=={'candidate_occurrences':0,'baseline_occurrences':0}
report=dict(candidate_source_sha256=sha(a/'qkd_host_native_engine.sv'),baseline_source_sha256=sha(b/'qkd_host_native_engine.sv'),candidate_mapped_sha256=sha(a/'original.v'),baseline_mapped_sha256=sha(b/'original.v'),candidate_map_log_sha256=sha(a/'map.log'),baseline_map_log_sha256=sha(b/'map.log'),candidate_warnings=len(wa),baseline_warnings=len(wb),normalized_missing=missing,normalized_extra=extra,warned_temporary_connectivity=absence,scope='same exact selected params/script/toolimage/library; semantic warning headers paired after generated-ID/source-line normalization; full diagnostic logs retained; no blanket whole mapping/cold qualification')
(a/'warning_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
folders={
'native_candidate':(a,['original.v','qkd_host_native_engine_n32.sv','qkd_host_native_engine_n32.json','copy_certificate.json','copy_cones.json','poison_connectivity.json','warning_comparison.json','map.log','map.stdout.log','map.sh','run_native.sh','tool_image.txt','yosys.version','source_library.sha256','engine_native32.py','engine_copy_certificate.py','audit_physical_copy_cones.py','bind_copy_inputs.py','native_raw.json','native_raw.log']),
'baseline':(b,['map.log','map.sh','source_library.sha256','yosys.version']),
'canonical_native':(root/'hroot-address-resynth-1021',['native_canonical.json','native_canonical.log','census_command.json','resynth.log','resynth.v','resynth.sh','census.py','native_census.py','textbook_lint.py','native_canonical_missing_parser.log','census_command_missing_parser.json']),
'projection_timeout':(root/'hroot-address-projection-1021',['original.sv','candidate.sv','source_edit_audit.json','projection.log','projection.stdout.log']),
'projection_short_timeout':(root/'hroot-address-projection-r2-1021',['projection_short.log','projection_short.stdout.log']),
'composition':(root/'hroot-address-composition-1021',['original.sv','candidate_lowered.sv','source_edit_audit.json','contract_application.json','composition.log','composition.stdout.log']),
'frontend_refusal':(root/'hroot-address-map-inputs-1021',['map.log','map.stdout.log','map_docker.log'])}
manifest={}
for label,(src,names) in folders.items():
 dst=out/label;dst.mkdir(exist_ok=True)
 for name in names:
  p=src/name;assert p.exists(),str(p);raw=p.read_bytes();dest=dst/(name+'.gz' if len(raw)>120000 else name)
  if dest.suffix=='.gz':dest.write_bytes(gzip.compress(raw,mtime=0))
  else:dest.write_bytes(raw)
  manifest[label+'/'+dest.name]={'source_path':str(p),'source_sha256':hashlib.sha256(raw).hexdigest(),'stored_sha256':sha(dest)}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('SEALED',out,'FILES',len(manifest),'WARNINGS',len(wa),len(wb))
