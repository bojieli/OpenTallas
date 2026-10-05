"""Archive terminal W12 evidence without restarting jobs or writing source trees."""
import argparse
import base64
import datetime
import hashlib
import json
import subprocess
import time
from pathlib import Path

SPOOL = Path('/tmp/claude-1000/w12b/terminal_spool_20261001')
JOBS = [
    ('tp4_su64_token', 'ot-pve1', 1217332, '/home/ubuntu/w12/rt_tp4d_token.json',
     ['/home/ubuntu/w12/rt_tp4d/token.log', '/home/ubuntu/w12/rt_tp4d/build_params.json']),
    ('ar256_su64_l0', 'ot-pve1', 1356870, '/home/ubuntu/w12bwork/seg/rt_l0.json',
     ['/home/ubuntu/w12bwork/seg/rt_l0.out', '/home/ubuntu/w12bwork/seg/rt/token.log', '/home/ubuntu/w12bwork/seg/rt/build_params.json']),
    ('tile_i518_replacement', 'ot-pve3', 1921558,
     '/home/ubuntu/w12bwork/src/results/physical_hdc/asap7/qwen_o4_w12/tile_i518/physical.json',
     ['/home/ubuntu/w12bwork/chain_i518.log']),
    ('tile_i560_replacement', 'ot-pve2', 2563050,
     '/home/ubuntu/w12bwork/src/results/physical_hdc/asap7/qwen_o4_w12/tile_i560/physical.json',
     ['/home/ubuntu/w12bwork/chain_i560.log']),
    ('spine_s833b', 'ot-pve2', 3091880,
     '/home/ubuntu/w12work/repo/results/physical_hdc/asap7/qwen_o4_w12/spine_s833b/physical.json',
     ['/home/ubuntu/w12work/spine_s833b.log']),
    ('partition_product_attempt2', None, 430286,
     '/home/ubuntu/qwen-recovery-jobs/partition_product_attempt2.json',
     ['/home/ubuntu/qwen-recovery-jobs/partition_product_attempt2.log', '/home/ubuntu/qwen-recovery-jobs/partition_product_attempt2.rc']),
]

# This probe is read-only, checks process existence before any collection, and
# transfers bounded terminal text evidence. Heavy checkpoints remain in place.
PROBE = '''import base64,hashlib,json,os
from pathlib import Path
pid,record,extras=INPUT
proc=Path('/proc').joinpath(str(pid))
alive=proc.exists()
if alive:
 try:alive=proc.joinpath('stat').read_text().rsplit(') ',1)[1].split()[0]!='Z'
 except OSError:alive=False
if alive:
 print(json.dumps({'state':'live','pid':pid}));raise SystemExit(0)
p=Path(record)
status='inconclusive'
if p.exists():
 r=json.loads(p.read_text())
 status=r.get('status')
if status not in ('pass','fail','error','inconclusive'):
 print(json.dumps({'state':'unrecognized_record','status':status}));raise SystemExit(0)
paths=[p]+[Path(x) for x in extras]
if p.name=='physical.json':
 paths += list(p.parent.glob('*.log'))+list(p.parent.glob('corners/*.json'))+list(p.parent.glob('corners/*.log'))
files={}
for f in paths:
 if not f.is_file():continue
 if f.stat().st_size>2*1024*1024:continue
 data=f.read_bytes()
 files[str(f)]={'sha256':hashlib.sha256(data).hexdigest(),'base64':base64.b64encode(data).decode()}
print(json.dumps({'state':'terminal','pid':pid,'status':status,'files':files}))
'''


def poll(job):
    name, host, pid, record, extras = job
    code = PROBE.replace('INPUT', repr((pid, record, extras)), 1)
    cmd = ['python3', '-'] if host is None else ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', host, 'python3', '-']
    p = subprocess.run(cmd, input=code, capture_output=True, text=True, timeout=30)
    if p.returncode:
        return {'state': 'probe_error', 'returncode': p.returncode, 'stderr': p.stderr[-1000:]}
    return json.loads(p.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--once', action='store_true')
    args = ap.parse_args()
    SPOOL.mkdir(exist_ok=True)
    while True:
        states = {}
        for job in JOBS:
            name, host, *_ = job
            dest = SPOOL / name
            if (dest / 'archive.json').exists():
                states[name] = {'state': 'already_archived'}
                continue
            try:
                data = poll(job)
            except Exception as exc:
                states[name] = {'state': 'probe_error', 'error': str(exc)}
                continue
            states[name] = {k: v for k, v in data.items() if k != 'files'}
            if data['state'] != 'terminal':
                continue
            # Never replace a previous archive, including partial/error intake.
            dest.mkdir(exist_ok=False)
            files = {}
            for index, (source, item) in enumerate(data['files'].items()):
                raw = base64.b64decode(item['base64'])
                assert hashlib.sha256(raw).hexdigest() == item['sha256']
                target = dest / f'{index:02d}_{Path(source).name}'
                with target.open('xb') as f:
                    f.write(raw)
                files[source] = {'local_file': target.name, 'sha256': item['sha256']}
            archive = {'collected_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       'host': host or 'local', 'job': name, 'raw_status': data['status'], 'files': files,
                       'claim_boundary': 'Raw terminal evidence only; independently verify source pins, exactness and SS/FF before adoption. TP4 runtime SU64 is not SU1024 product qualification.'}
            with (dest / 'archive.json').open('x') as f:
                f.write(json.dumps(archive, indent=2, sort_keys=True) + '\n')
        state = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'jobs': states}
        temp = SPOOL / 'state.tmp'
        temp.write_text(json.dumps(state, indent=2, sort_keys=True)+'\n')
        temp.replace(SPOOL / 'state.json')
        if args.once or all(v['state'] in ('terminal', 'already_archived') for v in states.values()):
            print(json.dumps(state, indent=2, sort_keys=True))
            return
        time.sleep(45)


if __name__ == '__main__':
    main()
