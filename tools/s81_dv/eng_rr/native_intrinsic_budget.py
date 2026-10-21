#!/usr/bin/env python3
"""Read completed native ODB for a zero-wire intrinsic budget, never a physical verdict.
No synthesis, placement, CTS, clock relaxation or source mutation. Preserve each report directory.
"""
import argparse,json,pathlib,subprocess,re,hashlib
p=argparse.ArgumentParser();p.add_argument('snapshot',type=pathlib.Path);a=p.parse_args();r=a.snapshot.resolve();w=r/'native';src=r/'src';out=r/'intrinsic_budget';out.mkdir(exist_ok=False)
census=json.loads((w/'native_census.json').read_text());manifest=json.loads((w/'source_manifest.json').read_text())
assert census['top']=='dsdv_eng_rr'and not census['role_errors']
odb=w/'results/asap7/opentallas_dsdv_eng_rr_asap7_native/base/1_synth.odb';assert odb.exists(),'native parser/ODB incomplete: no intrinsic read'
sdc=w/'constraint.sdc';assert re.search(r'-period\s+770\b',sdc.read_text()),'unexpected native clock profile'
receipt={'source':manifest['snapshot_commit'],'scope':'MODEL_ONLY_ZERO_WIRE_INTRINSIC_NOT_PHYSICAL_CLOSURE','native_status':census['status'],'period_ps':770,'uncertainty':'unchanged nativeSDC; no new uncertainty or interface budgets, not production signoff','wire':'No placement/parasitics/CTS; default ideal sourceclock with mapped clock inversions; no propagated clock added','odb_sha256':hashlib.sha256(odb.read_bytes()).hexdigest(),'sdc_sha256':hashlib.sha256(sdc.read_bytes()).hexdigest(),'corners':{}}
def q(t):
 assert not any(c in t for c in '{}\n\r'),'unsafe Tcl path'
 return '{'+t+'}'
for corner,pathkind in [('tt','max'),('ff','min')]:
 libs=[x for x in census['liberty']if re.search(r'_'+corner+r'(?:_|\.)',pathlib.Path(x['path']).name,re.I)]
 assert libs and any(x['path'].startswith('/src/')for x in libs),'missing exact memory/standardcellcorner'
 tcl=['# Read-only analytical native budget, no physical evidence.']
 tcl+=['read_liberty '+q(x['path'])for x in libs]
 tcl+=['set_units -time ps','read_db /native/results/asap7/opentallas_dsdv_eng_rr_asap7_native/base/1_synth.odb','read_sdc /native/constraint.sdc','puts "INTRINSIC_BUDGET_MODEL_ONLY_ZERO_WIRE_'+corner.upper()+'"','report_checks -path_delay '+pathkind+' -group_path_count 20 -format full_clock_expanded -fields {slew cap fanout} -digits 6','report_worst_slack -'+pathkind]
 fn=out/(corner+'.tcl');fn.write_text('\n'.join(tcl)+'\n')
 cmd=['docker','run','--rm','-v',str(src)+':/src:ro','-v',str(w)+':/native:ro','-v',str(out)+':/out','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/out/'+corner+'.tcl']
 with(out/(corner+'.log')).open('w')as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
 receipt['corners'][corner]={'returncode':rc,'libraries':libs,'log_sha256':hashlib.sha256((out/(corner+'.log')).read_bytes()).hexdigest()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('NATIVE_INTRINSIC_MODEL_ONLY',[(k,x['returncode'])for k,x in receipt['corners'].items()],flush=True)
raise SystemExit(any(x['returncode']for x in receipt['corners'].values()))
