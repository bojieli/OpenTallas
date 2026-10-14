#!/usr/bin/env python3
"""Export exact Git source blobs for the FIN1/FIN2 control oracle; edits no RTL."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('commit')
parser.add_argument('out', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
commit = subprocess.check_output(['git', 'rev-parse', args.commit + '^{commit}'], cwd=root, text=True).strip()
args.out.mkdir(parents=True, exist_ok=False)
files = []
for path in ['rtl/lib/ot_rst_relay.sv', 'rtl/hbm_accel/generic/ot_hgi_quant_record.sv',
             'rtl/hbm_accel/generic/qw/ot_hgi_qdq_fr.sv',
             'rtl/hbm_accel/generic/qw/ot_hgi_qdq_core.sv',
             'rtl/hbm_accel/generic/qw/ot_hgi_qdq_core_fin2.sv']:
    data = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=root)
    (args.out / Path(path).name).write_bytes(data)
    files.append({'path': path, 'sha256': hashlib.sha256(data).hexdigest(),
                  'git_blob': subprocess.check_output(['git', 'rev-parse', commit + ':' + path], cwd=root, text=True).strip()})
(args.out / 'source_manifest.json').write_text(json.dumps({'commit': commit, 'files': files}, indent=2) + '\n')
print(args.out / 'source_manifest.json')
