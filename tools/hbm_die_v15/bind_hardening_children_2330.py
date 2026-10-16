#!/usr/bin/env python3
"""Bind exact native DMA descendants without qualifying their wires-only parent."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    ('controller', '08fa61de3', 'hv15_dbk_vp4_ctl',
     'rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks.sv'),
    ('bank', 'bda78a0ad', 'hv15_dbk_bank',
     'rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp_banks.sv'),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(ref, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', ref + ':' + path])


def main():
    gf = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
    af = ROOT / 'results/arch/hbm_die_v15/native_view_admission.json'
    g, admission = json.loads(gf.read_text()), json.loads(af.read_text())
    records = {}
    for role, ref, kit, source in CASES:
        receipt = f'results/rtl/hbm_harden_2330/{role}_native_strict_bundle.json'
        audit = json.loads((ROOT / receipt).read_text())
        assert audit['pass'] and audit['routed']['tt_setup_ps'] >= 0 and audit['routed']['ff_hold_ps'] >= 0
        assert audit['routed']['drc'] == 0
        assert audit['launch_ps'] <= 220 and audit['capture_ps'] <= 190 and audit['spread_ps'] <= 80
        assert audit['comb_pins'] == 0
        view, master = audit['view'], audit['cell']
        # Validate all immutable audit artifacts, not just their filenames.
        for name, expected in audit['view_sha256'].items():
            assert sha((ROOT / view / name).read_bytes()) == expected, (role, name)
        provenance = ROOT / view / 'provenance/abstract_pin_stub.json'
        assert sha(provenance.read_bytes()) == audit['export_provenance_sha256']
        p = json.loads(provenance.read_text())
        assert p['status'] == 'PASS' and p['returncode'] == 0
        for field in ('input', 'output'):
            assert sha((ROOT / view / p[field]['path']).read_bytes()) == p[field]['sha256']
        assert sha((ROOT / view / p['helper']['retained_copy']).read_bytes()) == p['helper']['sha256']
        spec = json.loads(blob(ref, f'physical/ref_tile/{kit}/spec.json'))
        dependencies = {}
        for dep in spec['sources']:
            raw = blob(ref, dep)
            # Explicitly reject stale skipped working files after a sparse merge.
            assert (ROOT / dep).read_bytes() == raw, ('current source drift', role, dep)
            dependencies[dep] = sha(raw)
        files = {name: audit['view_sha256'][name] for name in
                 (master + '.lef', master + '_tt.lib', master + '_ff.lib', master + '_ss.lib', 'insertion.json')}
        files['provenance/abstract_pin_stub.json'] = audit['export_provenance_sha256']
        records[role] = dict(cell=master, view=view, source=source,
            source_sha256=dependencies[source], source_dependencies_sha256=dependencies,
            view_files_sha256=files, native_audit=receipt,
            native_metrics={k: audit[k] for k in ('R_ps', 'spread_ps', 'launch_ps', 'capture_ps')})
        admission['masters'][master] = dict(adopt=True,
            qualification='SOURCE_EXACT_NATIVE_DESCENDANT_ONLY', view=view,
            source=source, source_sha256=dependencies[source],
            source_dependencies_sha256=dependencies, view_sha256=files, receipt=receipt,
            reason='Strict source/view/export lineage and native TT/FF/DRC/pin/clock audit PASS; '
                'parent packing, power, incident paths and full-die qualification remain OPEN.')
    count = dict(controller=0, bank=0)
    for slot in g['slots']:
        if not slot['name'].startswith('hb_dbk_'):
            continue
        for child in slot['children']:
            role = 'controller' if child['inst'] == 'u_control' else 'bank'
            child.update(records[role], qualified_scope='Exact audited native descendant only; '
                'does not qualify parent clocks, PG, incident data paths or die.')
            count[role] += 1
        slot['controller_binding_status'] = 'One exact native-PASS registered-stk controller master; per-instance '
        slot['controller_binding_status'] += 'stk0/1/2/3 are explicit logical straps. Parent remains unqualified.'
        slot['parent_qualified'] = False
    assert count == dict(controller=4, bank=32), count
    g['native_hardening_binding_2330'] = dict(counts=count, parent_qualified=False,
        canonical_lineage_publication='c206b60b0',
        scope='Exact descendant binding; emitted parent geometry, PG, relay hops and roots remain OPEN.')
    gf.write_text(json.dumps(g, indent=1) + '\n')
    af.write_text(json.dumps(admission, indent=1) + '\n')
    print('PASS:4universal controller+32bank exact native descendants; parent qualification remains OPEN')


if __name__ == '__main__':
    main()
