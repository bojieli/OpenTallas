"""Strict additive R41 lineage admission for the production PC10 adapter.

Regenerate the complete extension from immutable source, never admit arbitrary
appends. Allocation semantics only; no arithmetic or hardware timing credit.
"""
import ast
import copy
import gzip
import hashlib
import json
from pathlib import Path
import h4_hbm_w19_pc10_endpoints as base

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/h4_hbm_pc10_r41_lineage_20261002'
PIN = '08544077bd807941f90833ed1b71d886dc2e84399473ba1818af88c2ac7fcfee'

def inputs():
    raw = (BASE / 'input_manifest.json').read_bytes()
    if base.sha(raw) != PIN:
        raise ValueError('lineage manifest pin')
    out = {}
    for row in json.loads(raw)['inputs']:
        p = (BASE / row['archive']).resolve()
        if not p.is_relative_to(BASE.resolve()):
            raise ValueError('lineage archive origin')
        b = p.read_bytes()
        if len(b) != row['bytes'] or base.sha(b) != row['sha256']:
            raise ValueError('lineage source pin')
        out[p.name] = b
    return out

def regenerate():
    s = inputs()
    original = base.decoded(base.inputs(), 'homes.json.gz')['homes']
    native = json.loads(gzip.decompress(s['native.json.gz']))
    manifest = json.loads(gzip.decompress(s['manifest.json.gz']))
    if base.sha(s['native.json.gz']) != manifest['native_program_sha256']:
        raise ValueError('original native source pin')
    # Execute only pinned storage allocation functions. R41 provider imports,
    # launch paths and all numerical executors are outside this closure.
    ns = {'copy': copy, 'hashlib': hashlib, 'canonical': base.canonical}
    for name, wanted in [('r30.py', {'BASE', 'CAP', 'FLOAT', 'INTEGER',
                                  'output_spec', 'compile_directory', 'patch_homes'}),
                         ('r41.py', {'bind_storage'})]:
        tree = ast.parse(s[name], filename=name)
        nodes = []
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and n.name in wanted:
                nodes.append(n)
            elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in wanted for t in n.targets):
                nodes.append(n)
            elif name == 'r30.py' and isinstance(n, ast.Import):
                # Allocation output sizes use source math.prod only.
                nodes.append(ast.Import(names=[ast.alias(name='math')]))
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), name, 'exec'), ns)
    patched, expanded, directory, report = ns['bind_storage'](native, original, manifest)
    if len(expanded) != len(original) + 4616 or len(directory['rows']) != 4616:
        raise ValueError('complete R41 extension count')
    if base.canonical(expanded[:len(original)]) != base.canonical(original):
        raise ValueError('original physical prefix changed')
    if report['effective_native_content_sha256'] != '9d538b80f1e8d3eada8ed4c967426bab5649339ff6fa2f0535eb393f7b15145d':
        raise ValueError('R41 full native regeneration')
    return original, expanded, patched

class ProductionPC10(base.ProductionPC10):
    def __init__(self, provider):
        original = base.decoded(base.inputs(), 'homes.json.gz')['homes']
        if base.canonical(provider.homes) == base.canonical(original):
            super().__init__(provider)
            self.lineage = 'original_exact'
            return
        if base.canonical(provider.homes[:len(original)]) != base.canonical(original):
            raise ValueError('original physical prefix changed')
        original, expanded, patched = regenerate()
        if base.canonical(provider.homes) != base.canonical(expanded):
            raise ValueError('complete source-regenerated R41 homes required')
        if not hasattr(provider, 'native') or base.canonical(provider.native) != base.canonical(patched):
            raise ValueError('complete source-regenerated R41 native required')
        # PC9/10 writes and referenced indices must be identical to the original
        # source. The R41 patch may only bind originally empty state outputs.
        native = json.loads(gzip.decompress(inputs()['native.json.gz']))
        for pc in (9, 10):
            if base.canonical(native['instructions'][pc]) != base.canonical(patched['instructions'][pc]):
                raise ValueError('PC9/10 referenced homes changed')
        self.homes = original
        self.provider = provider
        self.plan = next(p for p in base.decoded(base.inputs(), 'tiles.json.gz') if p['PC'] == 10)
        self.lineage = 'R41_full_source_regeneration'
