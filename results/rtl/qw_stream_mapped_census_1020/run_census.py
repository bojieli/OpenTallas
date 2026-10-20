#!/usr/bin/env python3
"""Read-only census of retained STREAM synthesis snapshots; no physical launch."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE
IMAGE = 'openroad/orfs:asap7lock'
JOBS = ['qfd_dv_stream_t2_1019-s2-49ac29c7e', 'qfd_dv_stream_t2c_1019-c2-49ac29c7e']

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    root = Path(sys.argv[1]).resolve()
    toolroot = Path(sys.argv[2]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    image_id = subprocess.check_output(['docker', 'inspect', IMAGE, '--format', '{{.Id}}'], text=True).strip()
    manifest = {'tool_commit': '940af34287955689574cb1231ae8d7049a925235',
                'image_tag': IMAGE, 'image_id_observed': image_id,
                'tool_sha256': sha(toolroot / 'tools/ref_tile/native_census.py'),
                'parser_sha256': sha(toolroot / 'tools/textbook_lint.py'), 'jobs': []}
    for job in JOBS:
        run = job.replace('-', '_')
        orig = Path('/srv/opentallas-scratch/claude/closure-loop') / job / 'routes' / run / 'work/orfs'
        suffix = Path('asap7') / ('opentallas_qfd_dv_stream_tile_asap7_ref_' + run) / 'base'
        netlist = orig / 'results' / suffix / '1_2_yosys.v'
        odb = orig / 'results' / suffix / '1_synth.odb'
        log = orig / 'logs' / suffix / '1_1_yosys_canonicalize.log'
        log2 = orig / 'logs' / suffix / '1_2_yosys.log'
        out = root / job
        out.mkdir(exist_ok=True)
        libs = list(dict.fromkeys(re.findall(r'Executing Liberty frontend: (\S+)', log.read_text())))
        if not libs:
            raise RuntimeError('No actual Liberty frontend entries: ' + str(log))
        entry = {'job': job, 'netlist': str(netlist), 'odb': str(odb),
                 'before': {str(p): sha(p) for p in (netlist, odb, log, log2)}, 'libraries': []}
        args = []
        for lib in libs:
            dest = out / Path(lib).name
            data = subprocess.check_output(['docker', 'run', '--rm', '--network=none', image_id, 'cat', lib])
            dest.write_bytes(data)
            entry['libraries'].append({'synthesis_log_path': lib, 'snapshot': str(dest), 'sha256': sha(dest)})
            args += ['--liberty', str(dest)]
        for p in (log, log2):
            (out / p.name).write_bytes(p.read_bytes())
        cmd = [sys.executable, str(toolroot / 'tools/ref_tile/native_census.py'),
               '--netlist', str(netlist), '--top', 'qfd_dv_stream_tile', *args, '--out', str(out / 'native_census.json')]
        with (out / 'census.log').open('w') as stream:
            result = subprocess.run(cmd, stdout=stream, stderr=subprocess.STDOUT)
        entry.update(census_argv=cmd, census_exit=result.returncode,
                     after={str(p): sha(p) for p in (netlist, odb, log, log2)})
        entry['immutable'] = entry['before'] == entry['after']
        manifest['jobs'].append(entry)
        (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        report = json.loads((out / 'native_census.json').read_text())
        print(job, result.returncode, report.get('status'), 'max', report.get('max_dynamic_loads'),
              'violations', len(report.get('violations', [])), 'role_errors', len(report.get('role_errors', [])), flush=True)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
