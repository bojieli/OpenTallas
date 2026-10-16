#!/usr/bin/env python3
"""Apply the fourteen DEDUPE phase-1 station/relay standard bundle-recovery receipts (S-NET+FILL, 10-16).

Same receipt schema as the canonical6 / successors recovery (export_provenance schema 1): for each PASSED replay
(raw final-ODB LEF hash == immutable original manifest, helper output == published LEF byte-for-byte) this writes
views/<cell>/provenance/{view_export.abstract.json, raw/<cell>.lef, helper/abstract_pin_stub.py, reconstruction/*,
abstract_pin_stub.json} and links it from abstract.json. Fails closed: refuses a view that already has provenance/,
a current file that differs from the replayed published hash, or an abstract.json whose LEF hash is not the raw hash.

Helper basis: 11 replays used the job-source helper (source_commit). hstnv_515/759/2204 (source c6e3baa04) actually
installed the verified frozen overlay helper (route_overlay_plan, helper_overlay_verification verified_original);
their receipts name THAT basis (git blob / origin_main / content hash), not the c6 source branch.
usage: apply_standards14.py WORKTREE ART_DIR [BATCH ... --out NAME]  (default batches standards14 standards3_effective)
"""
import hashlib, json, shutil, sys
from pathlib import Path

w = Path(sys.argv[1]).resolve(); art = Path(sys.argv[2]).resolve()
args = sys.argv[3:]; OUT = 'recovered_standards14_0040.json'
if '--out' in args:
    i = args.index('--out'); OUT = args[i + 1]; args = args[:i] + args[i + 2:]
BATCHES = args or ['standards14', 'standards3_effective']
sys.path.insert(0, str(w / 'tools/ref_tile')); sys.path.insert(0, str(w / 'tools/hier_contract'))
import export_provenance as EP  # noqa: E402
import child_lint as C  # noqa: E402
import native_pin_audit as N  # noqa: E402
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

ADMISSION = {  # ot-run units that executed the replays (logs in ART_DIR/standards14, standards3_effective)
    ('standards14', 'ot-epyc1tb'): 'oth-ubuntu-2094769-1792135225', ('standards14', 'ot-epyc4'): 'oth-ubuntu-3757852-1792135225',
    ('standards14', 'ot-pve1'): 'oth-ubuntu-1870763-1792135225',
    ('standards3_effective', 'ot-epyc1tb'): 'oth-ubuntu-2134426-1792135703',
    ('standards3_effective', 'ot-epyc4'): 'oth-ubuntu-3784147-1792135703',
    ('xstg_n4', 'ot-epyc1tb'): 'oth-ubuntu-2148971-1792135864'}

rows = {}
for batch in BATCHES:
    for rp in sorted((art / batch).glob('ot-*/*/replay.json')):
        r = json.loads(rp.read_text())
        if r.get('passed'):
            rows[r['job']] = (batch, rp.parent.parent.name, rp.parent, r)
out = []
for job, (batch, host, d, r) in sorted(rows.items()):
    v = w / r['view']; cell = r['cell']; p = v / 'provenance'
    if p.exists():
        raise SystemExit(f'{cell}: provenance/ already present, refusing to rewrite historical evidence')
    for f, h in r['published_hashes'].items():
        if sha(v / f) != h:
            raise SystemExit(f'{cell}: current {f} differs from the replayed published hash')
    assert sha(d / 'raw.lef') == r['raw_sha256'] and sha(d / 'final.lef') == r['final_sha256'] == r['published_hashes'][cell + '.lef']
    inv = EP.check_invariants((d / 'raw.lef').read_text(), (d / 'final.lef').read_text(), C.parse_lef)
    lint = C.lint(str(v / (cell + '.lef')), str(v))
    if lint['verdict'] != 'PASS':
        raise SystemExit(f'{cell}: child_lint {lint["verdict"]}')
    rawmanifest = (v / 'abstract.json').read_bytes(); a = json.loads(rawmanifest)
    if not a.get('ok') or a['files'][cell + '.lef'] != r['raw_sha256']:
        raise SystemExit(f'{cell}: abstract.json LEF hash is not the raw export hash')
    (p / 'raw').mkdir(parents=True); (p / 'helper').mkdir(); (p / 'reconstruction').mkdir()
    (p / 'view_export.abstract.json').write_bytes(rawmanifest)
    shutil.copy2(d / 'raw.lef', p / 'raw' / (cell + '.lef')); shutil.copy2(d / 'helper.py', p / 'helper/abstract_pin_stub.py')
    for name in ('raw.tcl', 'raw_export.log', 'processor.log', 'replay.json'):
        shutil.copy2(d / name, p / 'reconstruction' / name)
    eh = r.get('effective_helper')
    helper = {'path': 'tools/hier_contract/abstract_pin_stub.py', 'sha256': r['helper_sha256'],
              'retained_copy': 'provenance/helper/abstract_pin_stub.py'}
    if eh and eh['basis'] == 'verified_original_frozen_overlay':
        assert eh['sha256'] == r['helper_sha256']
        helper.update(basis='verified_original_frozen_overlay', git_blob=eh['git_blob'], overlay_origin_main=eh['origin_main'],
                      overlay_content_sha256=eh['content_sha256'], overlay_verification=eh['verification'],
                      job_source_commit=r['source_commit'],
                      note='the route installed this frozen overlay helper; the job source commit helper does NOT reproduce the published LEF')
    else:
        helper.update(basis='job_source_commit', source_commit=r['source_commit'])
    receipt = {'schema': 1, 'kind': 'abstract_pin_stub', 'status': 'PASS',
               'input': {'path': f'provenance/raw/{cell}.lef', 'sha256': r['raw_sha256']},
               'output': {'path': f'{cell}.lef', 'sha256': r['final_sha256']}, 'helper': helper,
               'environment': r['environment'],
               'command': ['python3', 'provenance/helper/abstract_pin_stub.py', f'provenance/raw/{cell}.lef', f'{cell}.lef'],
               'returncode': 0, 'stdout': r['processor_summary'] + '\n', 'stderr': '', 'invariants': inv, 'child_lint': lint,
               'replay': {'historical': True, 'job': job, 'source_commit': r['source_commit'],
                          'published_record_commit': r['record_commit'], 'orfs_dir': r['orfs_dir'],
                          'raw_export_tcl': 'provenance/reconstruction/raw.tcl', 'raw_export_tcl_sha256': sha(d / 'raw.tcl'),
                          'environment_basis': r['environment_basis'], 'raw_matches_original_manifest': True,
                          'final_matches_published_export': True, 'all_published_files_verified': r['published_hashes'],
                          'admission': {'host': host, 'unit': ADMISSION[(batch, host)], 'memory_gb': 4, 'threads': 1}}}
    EP.write_json(p / 'abstract_pin_stub.json', receipt)
    a['files'][cell + '.lef'] = r['final_sha256']
    a['export_provenance'] = {'schema': 1, 'raw_manifest': 'provenance/view_export.abstract.json',
                              'raw_manifest_sha256': sha(p / 'view_export.abstract.json'),
                              'transformation': 'provenance/abstract_pin_stub.json',
                              'transformation_sha256': sha(p / 'abstract_pin_stub.json')}
    EP.write_json(v / 'abstract.json', a)
    nat = N.audit_one((str(w), cell, r['view']))
    out.append({'cell': cell, 'job': job, 'helper_basis': helper['basis'], 'raw_sha256': r['raw_sha256'],
                'final_sha256': r['final_sha256'], 'child_lint': lint['verdict'], 'native_pass': nat['pass'],
                'launch_ps': nat.get('launch_ps'), 'capture_ps': nat.get('capture_ps'), 'spread_ps': nat.get('spread_ps'),
                'fail_why': nat.get('fail_why', ''),
                'transformation_sha256': a['export_provenance']['transformation_sha256']})
    print(cell, helper['basis'], 'native', 'PASS' if nat['pass'] else 'FAIL ' + nat.get('fail_why', ''))
EP.write_json(w / 'results/arch/native_pin_audit_snetfill_1015' / OUT,
              {'scope': 'DEDUPE phase-1 S81 station/relay standards: strict export lineage + native pin audit only; '
                        'no die slot/pin binding or parent/die qualification', 'rows': out})
print(len(out), 'receipts applied')
