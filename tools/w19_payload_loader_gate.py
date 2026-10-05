#!/usr/bin/env python3
"""Gate the model-sized host loader on four retained connected SM fixtures.

Historical exactness stays at its original source pin. Fresh replay compares the
complete output to the audited retained run; it does not regenerate a checkpoint
golden, certify 96 ranks, or establish physical timing or token performance.
"""
import argparse
import shutil
from w19_payload_loader import load_image
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def git_bytes(pin, path):
    return subprocess.check_output(['git', 'show', pin + ':' + path], cwd=ROOT)

def audit(record, fixtures):
    assert record['status'] == 'pass' and len(record['cases']) == 60
    assert all(c['gate_pass'] for c in record['cases'])
    for p, expected in record['source_sha256'].items():
        assert hashlib.sha256(git_bytes(record['source_commit'], p)).hexdigest() == expected, p
    for p, expected in record['sm_snapshot']['source_sha256'].items():
        assert hashlib.sha256(git_bytes(record['sm_snapshot']['commit'], p)).hexdigest() == expected, p
    directories = {}
    for d in fixtures.glob('s_*'):
        if (d / 'cfg.hex').exists():
            directories.setdefault(sha(d / 'cfg.hex'), []).append(d)
    matched = []
    for c in record['cases']:
        pins = c['rtl']['fixture_sha256']
        candidates = [d for d in directories.get(pins['cfg.hex'], [])
                      if all(sha(d / p) == h for p, h in pins.items())]
        assert len(candidates) == 1, (c['op'], 'missing or ambiguous fixture')
        d = candidates[0]
        text = (d / 'out.txt').read_text()
        assert 'TIMEOUT' not in text
        rows = [line for line in text.splitlines() if not line.startswith('#')]
        assert len(rows) == c['sm_rows'][1] - c['sm_rows'][0]
        assert len({line.split()[0] for line in rows}) == len(rows)
        matched.append((c, d))
    assert sum(c['exact'] for c, _ in matched) == 36
    assert sum(c['corrupt_exponent'] for c, _ in matched) == 18
    assert sum(c['row_swap'] for c, _ in matched) == 6
    return matched

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--historical-record', type=Path, required=True)
    ap.add_argument('--fixtures', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--record', type=Path, required=True)
    ap.add_argument('--host', required=True)
    ap.add_argument('--ssh-key', type=Path, required=True)
    ap.add_argument('--remote-work', required=True)
    a = ap.parse_args()
    if a.record.exists(): raise SystemExit('Refusing to overwrite evidence')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT).strip():
        raise SystemExit('Requires clean committed source')
    a.work.mkdir(parents=True, exist_ok=True)
    old = json.loads(a.historical_record.read_text())
    matched = audit(old, a.fixtures)
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    import uarch_model as U
    design = U.hbm_gpu_design('v41')
    model = U.gpu_payload_transport_model()
    model.update(loader_scope='Already-sized host load-time swizzle; no engine or router RTL added',
                 loader_buffer_bytes_bound=167, model_source_sha256=sha(ROOT/'tools/uarch_model.py'), element=design['element'],
                 sm_count=design['sm_count'], bulk_copy=design['bulk_copy'])
    (a.work/'model_preflight.json').write_text(json.dumps(model,indent=2)+'\n')
    sources = []
    pins = {}
    for p, h in old['sm_snapshot']['source_sha256'].items():
        dest = a.work / Path(p).name
        dest.write_bytes(git_bytes(old['sm_snapshot']['commit'], p))
        sources.append(dest); pins[p] = h
    local = ['rtl/gpu/ot_gpu_payload_assemble.sv','rtl/gpu/ot_gpu_expert_fetch.sv',
             'rtl/hdc/kv/ot_hdc_hbm_model.sv','rtl/test/tb_w19_payload_loader.sv']
    for p in local:
        if p != 'rtl/test/tb_w19_payload_loader.sv':
            assert sha(ROOT/p) == old['source_sha256'][p], 'Changed connected RTL: '+p
        dest = a.work / Path(p).name
        dest.write_bytes((ROOT/p).read_bytes()); sources.append(dest); pins[p] = sha(dest)
    assert len({s.name for s in sources}) == len(sources)
    ssh = ['ssh','-i',str(a.ssh_key),a.host]
    scp = ['scp','-q','-i',str(a.ssh_key)]
    def remote(command):
        return subprocess.check_output(ssh+[command],text=True)
    remote('mkdir -p '+shlex.quote(a.remote_work))
    subprocess.run(scp+[str(s) for s in sources]+[a.host+':'+a.remote_work+'/'],check=True)
    compile_cmd = 'cd '+shlex.quote(a.remote_work)+' && iverilog -g2012 -s tb_w19_payload_loader -Ptb_w19_payload_loader.NC=1 -o sim.vvp '
    compile_cmd += ' '.join(shlex.quote(s.name) for s in sources)
    remote(compile_cmd)
    runtime = remote('iverilog -V 2>/dev/null | head -1; vvp -V 2>&1 | head -1')
    executable_pin = remote('sha256sum '+shlex.quote(a.remote_work+'/sim.vvp')).split()[0]
    chosen = []
    for family in ('w1','w3','w2'):
        chosen.append(next(pair for pair in matched if pair[0]['tag'].endswith(family)
                           and not pair[0]['stall']))
    for stall, corrupt, swap in ((1,False,False),):
        chosen.append(next(pair for pair in matched if pair[0]['tag'].endswith('w2')
                      and (pair[0]['stall'],pair[0]['corrupt_exponent'],pair[0]['row_swap'])==(stall,corrupt,swap)))
    results = []
    loader_records = []
    for i,(c,d) in enumerate(chosen):
        target = a.remote_work+'/case'+str(i)
        remote('mkdir -p '+shlex.quote(target))
        staged = a.work / ('case'+str(i)); staged.mkdir()
        for p in ('cfg.hex','lines.hex','x.hex'): shutil.copyfile(d/p,staged/p)
        loader_records.append(load_image(staged/'lines.hex',staged/'payload_sectors.hex',
            expected_sha256=c['rtl']['fixture_sha256']['lines.hex'],
            payloads=c['rtl']['lines'],expert_id=c['expert_id']))
        subprocess.run(scp+[str(staged/p) for p in ('cfg.hex','x.hex','lines.hex','payload_sectors.hex')]
            +[a.host+':'+target+'/'],check=True)
        remote('cd '+shlex.quote(target)+' && vvp -n '+shlex.quote(a.remote_work+'/sim.vvp')+' +DIR=. +GAP=0 > sim.log 2>&1')
        out = a.work / ('case'+str(i)+'.out')
        subprocess.run(scp+[a.host+':'+target+'/out.txt',str(out)],check=True)
        results.append(dict(op=c['op'],tag=c['tag'],stall=c['stall'],corrupt_exponent=c['corrupt_exponent'],
                            row_swap=c['row_swap'],fixture_sha256=c['rtl']['fixture_sha256'],
                            output_sha256=sha(out),reference_output_sha256=sha(d/'out.txt'),
                            pass_output=out.read_bytes()==(d/'out.txt').read_bytes()))
        print('replay',i,results[-1]['pass_output'],flush=True)
    result = dict(schema='opentallas.w19.payload_loader_gate.v1',status='pass' if all(r['pass_output'] for r in results) else 'fail',
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  historical_record_sha256=sha(a.historical_record),historical_source_commit=old['source_commit'],
                  historical_cases_audited=60,historical_exact=36,exponent_controls=18,row_swap_controls=6,
                  model_preflight=model,connected_source_sha256=pins,host=a.host,remote_work=a.remote_work,
                  runtime=runtime,executable_sha256=executable_pin,cases=results,loader_records=loader_records,
                  loader_source_sha256=sha(ROOT/'tools/w19_payload_loader.py'),
                  gate_source_sha256=sha(Path(__file__)),
                  claim_boundary='Four freshly compiled loader/HBM/fetch/sector-adapter/SM output replays against retained golden-bound outputs. Production host loader replaces bench packing only; retained sector proof reused. No checkpoint decoding, router or full 96-rank runtime, full token, physical closure, measured token gain or adoption claim.')
    a.record.write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='pass' else 1

if __name__=='__main__':
    raise SystemExit(main())
