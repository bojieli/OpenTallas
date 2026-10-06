import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import time

J = Path(__file__).resolve().parent
OLD = Path('/srv/opentallas-scratch/codex/noether-qx-exact-restart-r4-20261005/work/pos')
SRC = J / 'src'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

def capacity(stage):
    def cpu():
        return list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    a = cpu(); time.sleep(5); b = cpu()
    mem = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
    inventory = sum(p.stat().st_size for p in OLD.rglob('*') if p.is_file())
    result = dict(stage=stage, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  load1=os.getloadavg()[0], idle_cores_5s=(b[3]-a[3])/os.sysconf('SC_CLK_TCK')/5,
                  required_cores=3, mem_available_bytes=mem['MemAvailable']*1024,
                  disk_free_bytes=shutil.disk_usage(J).free, old_build_inventory_bytes=inventory,
                  required_disk_bytes=3*inventory+(J/'source.tar').stat().st_size,
                  reservation_GiB=16)
    with (J/'capacity.jsonl').open('a') as f: f.write(json.dumps(result)+'\n')
    return result['idle_cores_5s'] >= 3 and result['disk_free_bytes'] >= result['required_disk_bytes']

if '--admitted' not in sys.argv:
    while not capacity('before-unchanged-guard'): time.sleep(45)
    os.execv('/srv/opentallas-scratch/admit.sh', ['admit.sh', '16', '--', sys.executable, str(J/'run.py'), '--admitted'])
if not capacity('actual-exec'):
    os.execv(sys.executable, [sys.executable, str(J/'run.py')])

manifest = json.loads((J/'source.json').read_text())
assert all(hashlib.sha256((SRC/p).read_bytes()).hexdigest() == h for p,h in manifest['files'].items())
assert not subprocess.check_output(['git','status','--porcelain'], cwd=SRC)
d = runpy.run_path(str(SRC/'tools/dsrom_qx_exact.py'))
work = J/'work'/'pos'
work.parent.mkdir(exist_ok=True)
if not work.exists(): subprocess.run(['cp','-a','--reflink=auto',str(OLD),str(work)], check=True)
cmd = [str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'), '--binary','--timing',
       '-Wno-fatal','-Wno-lint','-Wno-style','--top-module','tb_dsrom_qx_exact',
       '--Mdir',str(work),'-j','2','-CFLAGS','-O1',*d['BUILDS']['pos'],
       *[str(SRC/p) for p in d['RTL']],str(SRC/d['TB'])]
(J/'build.command.json').write_text(json.dumps(cmd)+'\n')
(J/'started.json').write_text(json.dumps(dict(pid=os.getpid(), utc=time.time(), source_commit=manifest['source_commit']))+'\n')
with (J/'build.log').open('w') as f:
    rc = subprocess.run(['/usr/bin/time','-v',*cmd],cwd=SRC,stdout=f,stderr=subprocess.STDOUT).returncode
(J/'build.rc').write_text(str(rc)+'\n')
record = dict(schema='opentallas.dsrom_qx.exact_restart_repair.v1', verdict='FAIL',
              scope='QX10 pos seed1 NRAND400 +24 directed same-configuration mid-drain restarts and neg_tree9 seed1; not whole campaign qualification',
              source=manifest, build_returncode=rc, engine_changed=False,
              comparison_changed=False, old_live_jobs_preserved=True)
if rc == 0:
    command = [str(work/'Vtb_dsrom_qx_exact'),'+seed=1']
    (J/'run.command.json').write_text(json.dumps(command)+'\n')
    with (J/'seed1.log').open('w') as f:
        result = subprocess.run(['/usr/bin/time','-v',*command], cwd=J, stdout=f, stderr=subprocess.STDOUT)
    log = (J/'seed1.log').read_text()
    match = d['PASS'].search(log)
    record['run_returncode'] = result.returncode
    record['log_sha256'] = hashlib.sha256(log.encode()).hexdigest()
    if result.returncode == 0 and match:
        record['verdict'] = 'PASS'
        record['coverage'] = dict(zip(d['KEYS'],map(int,match.groups())))
    else: record['failure_excerpt'] = log[-3000:]
(J/'result.json').write_text(json.dumps(record,indent=2)+'\n')
if record['verdict'] == 'PASS':
    while not capacity('before-negative-control'): time.sleep(45)
    neg = J/'work'/'neg_tree9'
    original = Path('/srv/opentallas-scratch/claude/dsrom-qtclose/exact_qx10/work/neg_tree9')
    if not neg.exists(): subprocess.run(['cp','-a','--reflink=auto',str(original),str(neg)],check=True)
    negcmd = cmd[:cmd.index('-CFLAGS')+2] + d['BUILDS']['neg_tree9'] + [str(SRC/p) for p in d['RTL']] + [str(SRC/d['TB'])]
    negcmd[negcmd.index('--Mdir')+1] = str(neg)
    (J/'negative.build.command.json').write_text(json.dumps(negcmd)+'\n')
    with (J/'negative.build.log').open('w') as f:
        nrc = subprocess.run(['/usr/bin/time','-v',*negcmd],cwd=SRC,stdout=f,stderr=subprocess.STDOUT).returncode
    record['negative_build_returncode'] = nrc
    if nrc == 0:
        with (J/'negative.log').open('w') as f:
            nrc = subprocess.run([str(neg/'Vtb_dsrom_qx_exact'),'+seed=1'],cwd=J,stdout=f,stderr=subprocess.STDOUT).returncode
        nlog = (J/'negative.log').read_text()
        record['negative'] = dict(name='neg_tree9',seed=1,returncode=nrc,caught=nrc!=0 and ('mismatch' in nlog or 'divergence' in nlog),log_sha256=hashlib.sha256(nlog.encode()).hexdigest(),excerpt=nlog[-2000:])
        if not record['negative']['caught']: record['verdict']='FAIL'
    else: record['verdict']='FAIL'
    (J/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    (J/'done').write_text(record['verdict']+'\n')
if not (J/'done').exists(): (J/'done').write_text(record['verdict']+'\n')
