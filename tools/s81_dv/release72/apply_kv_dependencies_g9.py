#!/usr/bin/env python3
"""Complete exact existing production KV math source dependencies; no RTL edits."""
import argparse, hashlib, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / 'results/arch/s81_die72_1021/g9_assembly/kv_dependency_completion/manifest.json'

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--table', required=True, type=Path)
    a = ap.parse_args(); table = json.loads(a.table.read_text()); model = json.loads(MODEL.read_text())
    assert not table.get('kv_production_dependencies_g9'), 'KV dependency overlay already present'
    ref = model['source_ref']
    for path, h in model['source_sha256'].items():
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', ref+':'+path])
        assert hashlib.sha256(raw).hexdigest() == h, path
        paths = table.setdefault('rtl_refs', {}).setdefault(ref, [])
        if path not in paths: paths.append(path)
        prefer = table.setdefault('prefer', [])
        if ref+'/'+path not in prefer: prefer.append(ref+'/'+path)
    table['kv_production_dependencies_g9'] = {
        'source_ref': ref, 'source_sha256': model['source_sha256'],
        'direct_root_params': model['direct_root_params'],
        'scope': 'Exact production dependency closure, no source/body/edge changes; failed3181539 retained, onlyKV elaboration completion; no runtime/physical promotion',
        'fastfp': 'Explicit productionff9 source; qmul/qadd now reachable forKV. Original0Npass446 inventory remains independent.'}
    a.table.write_text(json.dumps(table, indent=1)+'\n')
    print('G9_KV_PRODUCTION_DEPENDENCIES exact16files/43module conservative closure; KV-only elaboration owed')

if __name__ == '__main__': main()
