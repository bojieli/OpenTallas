"""Harvest only after final SS/FF binding and coverage pass; no job/state writes."""
import hashlib
import io
import json
import pathlib
import re
import subprocess
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
launch = json.loads((HERE / 'audit_launch.json').read_text())
old = json.loads((HERE / 'audit_launch_v1.json').read_text())
remote = r'''
import hashlib,io,json,pathlib,re,sys,tarfile
r,a,old=map(pathlib.Path,sys.argv[1:]);e=r/'cl/eco-r2/pass1';v=r/'routes/dshead_elemB_ss_a318fdf47';b=next((e/'orfs/results/asap7').glob('*/base'));installed=next((v/'work/orfs/results/asap7').glob('*/base'))
assert (a/'complete').read_text().strip()=='PASS'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cs=json.loads((e/'corner_sta.json').read_text());result=json.loads((r/'cl/eco-r2/result.json').read_text());ex=json.loads((v/'view/export.json').read_text());proof=json.loads((a/'input_binding.json').read_text())
assert result['ss_ps']>=15 and result['ff_ps']>=15 and result['drc']==0 and not result['errors']
for ext in ('odb','sdc','spef'):
 h=sha(b/('6_final.'+ext));assert h==cs['setup_ss'][ext+'_sha256']==cs['hold_ff'][ext+'_sha256']==sha(installed/('6_final.'+ext))==proof['binding'][ext]
for rel,h in cs['post_sdc'].items():assert sha(r/'src'/rel)==h
for rel,h in {**proof['source_files'],**proof['macros']}.items():assert sha(r/'src'/rel)==h
for c,k,ws in [('ss','setup_ss','ws_max'),('ff','hold_ff','ws_min')]:
 assert ex[c]['done'] and abs(float(ex[c][ws])*1e12-cs[k]['worst_slack_ps'])<0.01
 assert not cs[k]['errors']
 log=(a/f'bind_{c}.log').read_text();assert f'OT_BIND_DONE {c} ' in log and '[ERROR' not in log and not re.search(r'^Error:',log,re.M)
 assert len(re.findall(r'^OT_BIND_MACRO '+c+' ',log,re.M))==26
for n,h in ex['files'].items():assert sha(v/'view'/n)==h
elog=(e/'eco_ff.log').read_text();assert re.findall(r'Number of violations = (\d+)',elog)[-1]=='0'
assert (r/'cl/hold_eco.a2.rc').read_text().strip()=='0' and (r/'cl/eco_install.a2.rc').read_text().strip()=='0'
files={
 'candidate/corner_sta.json':e/'corner_sta.json','candidate/result.json':r/'cl/eco-r2/result.json',
 'candidate/route_6_final.sdc':b/'6_final.sdc','candidate/eco_ff.log':e/'eco_ff.log',
 'history/first_eco_result.json':r/'cl/eco/result.json','history/pre_eco_corner_sta.json':v/'corner_sta.json.pre_eco',
 'history/original_physical.json':v/'physical.json','history/coverage_v1_ss.log':old/'bind_ss.log',
 'history/coverage_v1_ss.tcl':old/'bind_ss.tcl','candidate/eco_install.log':r/'cl/eco_install.a2.log',
 'candidate/eco_install.sh':r/'cl/eco_install.a2.sh','candidate/eco_install.rc':r/'cl/eco_install.a2.rc',
 'candidate/hold_eco.rc':r/'cl/hold_eco.a2.rc','candidate/hold_eco.sh':r/'cl/hold_eco.a2.sh',
 'constraints/signoff_elemB.sdc':r/'src/physical/dsrom_fh_safe/gen/signoff_elemB.sdc',
 'constraints/calib.json':r/'cl/calib.json','coverage/input_binding.json':a/'input_binding.json',
 'coverage/admission.log':a/'admission.log','coverage/run.sh':a/'run.sh'}
for c in ('ss','ff'):
 for ext in ('tcl','log'):files[f'coverage/bind_{c}.{ext}']=a/f'bind_{c}.{ext}'
 files[f'constraints/effective_{c}.sdc']=a/f'effective_{c}.sdc'
 files[f'candidate/w18_sta_{c}.tcl']=e/'orfs'/f'w18_sta_{c}.tcl'
 files[f'candidate/w18_sta_{c}.log']=e/'orfs'/f'w18_sta_{c}.log'
 files[f'candidate/w18_export_{c}.tcl']=v/'work/orfs'/f'w18_export_{c}.tcl'
for p in (v/'view').iterdir():
 if p.is_file():files['export/'+p.name]=p
for rel in proof['source_files']:files['source/'+rel]=r/'src'/rel
for rel in proof['macros']:files['source/'+rel]=r/'src'/rel
for n in ['hold_eco.sh','hold_eco.tcl','hold_eco_corner.tcl','hold_eco_window.tcl','hold_eco_sdc.py']:files['helpers/'+n]=r/'cl'/n
for n in ['corner_sta.py','export_view.py']:files['source/tools/w18/'+n]=r/'src/tools/w18'/n
manifest={'remote_run':str(r),'audit':str(a),'files':{n:{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for n,p in files.items()},'retained_bulk_artifacts':{str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in [b/'6_final.odb',b/'6_final.spef',b/'6_final.v',installed/'5_2_route.odb']}}
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 for n,p in files.items():t.add(p,arcname=n,recursive=False)
 data=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('remote_manifest.json');info.size=len(data);t.addfile(info,io.BytesIO(data))
'''
if not (HERE / 'export').exists():
    p = subprocess.run(['ssh', launch['host'], 'python3', '-', launch['run'], launch['audit'], old['audit']],
                       input=remote.encode(), capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(p.stdout), mode='r:') as archive:
        for entry in archive:
            rel = pathlib.PurePosixPath(entry.name)
            assert not rel.is_absolute() and '..' not in rel.parts and entry.isfile()
            dest = HERE / entry.name
            assert not dest.exists(), f'refuse overwrite: {dest}'
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.extractfile(entry).read())
manifest = json.loads((HERE / 'remote_manifest.json').read_text())
for rel, rec in manifest['files'].items():
    assert hashlib.sha256((HERE / rel).read_bytes()).hexdigest() == rec['sha256']
proof = json.loads((HERE / 'coverage/input_binding.json').read_text())
source_pin = 'a318fdf478cdce66e0b03d9d357fec14106713dd'
for rel, expected in {**proof['source_files'], **proof['macros']}.items():
    data = subprocess.check_output(['git', 'show', source_pin + ':' + rel], cwd=HERE)
    assert hashlib.sha256(data).hexdigest() == expected, ('source pin mismatch', rel)
cs = json.loads((HERE / 'candidate/corner_sta.json').read_text())
coverage = {}
for c in ('ss','ff'):
    log = (HERE / f'coverage/bind_{c}.log').read_text()
    line = re.search(r'^OT_BIND_DONE '+c+r' (.*)$', log, re.M).group(1)
    tokens = line.split();coverage[c] = dict(zip(tokens[::2],tokens[1::2]))
    assert coverage[c]['macro_count'] == '26'
    assert float(coverage[c]['macro_worst']) >= 15
    assert int(coverage[c]['outputs']) + int(coverage[c]['constants']) == 149
    effective = (HERE / f'constraints/effective_{c}.sdc').read_text()
    effective = re.sub(r"\\\s*\n", " ", effective)
    # Only the pre-existing reset false path is allowed in final signoff;
    # repair-only endpoint masks must not leak into final SDC/model export.
    exceptions = [x for x in effective.splitlines() if x.startswith('set_false_path')]
    assert exceptions and all('rst_n' in x for x in exceptions), exceptions
summary = {
 'schema': 'opentallas.elemB.final.v1', 'verdict': 'PASS',
 'job': 'dshead-elemB-ss-a318fdf47', 'source_commit': source_pin,
 'helper_commit': '6625a113964df4316b6c3ad5c56ed0630f21cb17',
 'ss_setup_ps': cs['setup_ss']['worst_slack_ps'], 'ff_hold_ps': cs['hold_ff']['worst_slack_ps'],
 'drc': 0, 'period_ps': 833.333, 'setup_uncertainty_ps': 60, 'hold_uncertainty_ps': 25,
 'io_delays_ps': {'input_max':784,'input_min':289,'output_max':-284,'output_min':-389},
 'coverage': coverage, 'binding': proof['binding'], 'image': proof['image'],
 'parameterization': json.loads((HERE/'history/original_physical.json').read_text())['design']['parameters'],
 'source_binding': 'All six design sources and SS/FF ROM Liberty plus ROM LEF match immutable source commit.',
 'export_binding': 'LEF/SS/FF Liberty hashes match export.json; exporter and final STA used the same installed ODB/SPEF/SDC, post-SDC and macro views; matching reported margins.',
 'constant_outputs': 'JOIN=0 outputs without timing paths are accepted only after proving a single TIELO/TIEHI driver in the signed-off ODB.',
 'prior_failure_preserved': {'ss_ps':92.02,'ff_ps':14.54,'location':'history/first_eco_result.json'},
 'new_eco_launched': False, 'existing_eco': 'eco-r2/pass1; 404 added cells; installed/exported remotely at 04:12',
 'workflow_note': 'Loop status/top-level metrics may lag completed eco_install. This result uses candidate and exported artifacts, not stale pre-ECO metrics. No shared job state changed.',
 'scope': 'Element-B block closure under the pinned IO/multicycle/reset contract; not new full-head/die context qualification.',
 'git_action': 'No commits, branch moves, staging, or pushes; parent commits explicit paths.'}
(HERE/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'verdict':summary['verdict'],'ss_ps':summary['ss_setup_ps'],'ff_ps':summary['ff_hold_ps'],'coverage':coverage,'export':str(HERE/'export')},indent=2))
