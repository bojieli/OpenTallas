from pathlib import Path
import subprocess,json,hashlib,shlex,datetime,os
j=Path('/srv/opentallas-scratch2/jobs/harvey-cp-parent-context-route-r1');r=j/'cts_failure_probe_r6';w=r/'work/orfs';src=j/'region_retry_r5/source'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['python3',str(j/'fresh_guard.py')],check=True)
d=next((w/'results').rglob('3_place.odb')).parent
assert sha(d/'3_place.odb')=='430bcb0a663240663afaa997941324957f9cb7af3e3c6ee7882474f25c7f8f24'
assert not (r/'started').exists()
flags=[];frozen={}
for p in d.iterdir():
 parts=p.stem.split('_')
 if p.suffix in ('.odb','.sdc','.v') and parts[0].isdigit() and int(parts[0])<=3 and 'error' not in p.name.lower():
  flags.extend(['-o','/work/'+str(p.relative_to(w))]);frozen[str(p)]=sha(p)
(r/'started').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n')
patch="""from pathlib import Path
import hashlib,json
p=Path('/OpenROAD-flow-scripts/flow/scripts/cts.tcl');s=p.read_text()
needle='  check_placement -verbose\\n';assert s.count(needle)==1
replacement='''  if {[catch {check_placement -verbose} ot_cp_capture_error]} {
    orfs_write_db /work/cts_failure.odb
    orfs_write_sdc /work/cts_failure.sdc
    puts OT_CP_CTS_FAILURE_CAPTURE
    error $ot_cp_capture_error
  }
'''
print(json.dumps(dict(original_cts_sha256=hashlib.sha256(s.encode()).hexdigest(),capture_only=True)))
p.write_text(s.replace(needle,replacement))
"""
(w/'capture_patch.py').write_text(patch)
cmd='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /work/capture_patch.py && make '+shlex.join(flags)+' DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 /work/'+str((d/'4_1_cts.odb').relative_to(w))
with (r/'cts_probe.log').open('w') as log:
 p=subprocess.Popen(['docker','run','--rm','-v',str(src)+':/src:ro','-v',str(w)+':/work','-w','/OpenROAD-flow-scripts/flow','openroad/orfs:asap7lock','bash','-lc',cmd],stdout=log,stderr=subprocess.STDOUT)
 (r/'docker_client.pid').write_text(str(p.pid)+'\n');rc=p.wait()
assert all(sha(Path(p))==h for p,h in frozen.items()),'upstream stage replayed'
(r/'probe.exit').write_text(str(rc)+'\n')
(r/'record.json').write_text(json.dumps(dict(scope='same-source CTS-only diagnosis from frozen placed checkpoint; capture error state only',source=str(src),checkpoint_sha256=sha(d/'3_place.odb'),frozen_inputs=frozen,source_phase_ps=0,setup_ps=60,hold_ps=25,NUM_CORES=16,exit=rc,failure_captured=(w/'cts_failure.odb').exists(),synthesis_floorplan_PDN_replayed=False),indent=2)+'\n')
(r/'terminal.exit').write_text(str(rc)+'\n')
