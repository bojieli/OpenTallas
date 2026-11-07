"""Receipt-backed HEAD PHY reset qualification in recovered-clock edges.

This supplies no core-cycle deadline, clock-period waiver or CDC exception.
The default reset checker remains unchanged without an explicit receipt.
"""
import hashlib
import json
from pathlib import Path


def digest(raw):
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def qualify(P, W, receipt_path):
    p = Path(receipt_path).resolve()
    r = json.loads(p.read_text())
    if r.get('schema') != 'opentallas.head_native_release.v1':
        raise ValueError('native release receipt schema')
    if r.get('plan_sha256') != digest(P.raw):
        raise ValueError('native release receipt plan identity mismatch')
    proof = r['proof']
    if proof.get('verdict') != 'PASS' or proof.get('guard_edges') != 66 or proof.get('leaf_edges') != 68:
        raise ValueError('native release requires measured 2+64 guard and two native synchronizer edges')
    if set(proof.get('mutants', {})) != {'early_hold', 'ignore_lock', 'leaf_reset', 'leaf_clock'}:
        raise ValueError('native release missing required mechanism/binding controls')
    if any(v != 'DETECTED' for v in proof['mutants'].values()):
        raise ValueError('native release mutant was not detected')
    required = {'cold', 'stopped_clock_lock_loss', 'stopped_clock_warm_reset'}
    if set(proof.get('epochs', [])) != required or proof.get('actual_codec_and_fifo') is not True:
        raise ValueError('native release must exercise actual production codec/FIFO and all reset epochs')
    if proof.get('actual_leaf_binding') is not True:
        raise ValueError('native release actual hard-leaf binding unproven')
    # Immutable proof inputs and logs travel with the receipt. No missing input
    # or changed source can inherit an old qualification.
    files = r.get('files', {})
    if not files or any(not isinstance(k, str) or not isinstance(v, str) for k, v in files.items()):
        raise ValueError('native release input closure missing')
    for name, sha in files.items():
        f = (p.parent / name).resolve()
        if hashlib.sha256(f.read_bytes()).hexdigest() != sha:
            raise ValueError('native release changed input: ' + name)
    runs = proof.get('runs', {})
    if set(runs) != {'positive', 'early_hold', 'ignore_lock', 'leaf_reset', 'leaf_clock'}:
        raise ValueError('native release run inventory incomplete')
    for name, run in runs.items():
        if run['log'] not in files:
            raise ValueError('native release log outside immutable closure')
        if run.get('bench') not in files:
            raise ValueError('native release fixture outside immutable closure')
        if name in ('positive', 'leaf_clock'):
            bench = (p.parent / run['bench']).read_text()
            if 'always @(leaf_clock or pck)' not in bench:
                raise ValueError('native release requires both-edge clock binding observation')
        text = (p.parent / run['log']).read_text()
        if name == 'positive':
            if run['returncode'] != 0 or 'HEAD_NATIVE_RELEASE PASS' not in text or 'leaf_binding=1' not in text:
                raise ValueError('native release positive run did not pass')
            for epoch in range(3):
                if f'HEAD_RELEASE epoch={epoch} guard_rck_edge=66 native_rck_edge=68' not in text:
                    raise ValueError('native release missing actual epoch measurement')
        elif run['returncode'] == 0 or 'FATAL:' not in text:
            raise ValueError('native release negative control did not fail: ' + name)
    import cores
    t = P.types.get('hd_serdes', {})
    contents = [c for c in t.get('contents', []) if c.get('inst') == 'u_phy']
    if len(contents) != 1:
        raise ValueError('native release requires one actual u_phy content')
    c = contents[0]
    if (c.get('module') != 'ot_s81hd_serdes_link_ls' or c.get('params', {}).get('LOCKSAFE') != 1
            or c.get('params', {}).get('HOLD_EDGES') != 64
            or any(c.get('bind', {}).get(k) != v for k, v in
                   {'pma_lock': 'pad:pma_lock', 'pma_rck': 'pad:pma_rck', 'ck': 'clk', 'rst_n': 'rst_n'}.items())):
        raise ValueError('native release plan does not bind the proved 64-edge locksafe mechanism')
    hard = [h for h in t.get('hard_cores', []) if h.get('inst') == 'u_phy.u_link.u_dec.u_chn']
    if len(hard) != 1 or hard[0].get('module') != 'ot_s81_kp4_dchn':
        raise ValueError('native release actual hard leaf differs from the proved production decoder')
    sources = proof.get('production_sources', {})
    expected = {'rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link_ls.sv',
                'rtl/dsrom_sys/s81_link/ot_pdie_serdes_locksafe.sv',
                'rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv',
                'rtl/dsrom_sys/s81_link/ot_s81_kp4_dec.sv',
                'rtl/dsrom_sys/s81_link/ot_s81_kp4_dchn.sv'}
    if not expected <= set(sources):
        raise ValueError('native release production source chain incomplete')
    for name, sha in sources.items():
        if hashlib.sha256(cores.resolve(name).read_bytes()).hexdigest() != sha:
            raise ValueError('native release actual production source changed: ' + name)
        if sha not in files.values():
            raise ValueError('native release proof source outside immutable closure')
    pending = W.get('release_qualification', {}).get('native_targets', [])
    bindings = r.get('bindings', [])
    canonical = lambda rows: sorted((x['part'], x['target'], x['native_clock_root']) for x in rows)
    if len(bindings) != 12 or len(set(canonical(bindings))) != 12 or canonical(bindings) != canonical(pending):
        raise ValueError('native release receipt must bind exactly all twelve actual native targets')
    for b in bindings:
        if (P.parts[b['part']]['type'] != 'hd_serdes' or b['target'] != 'u_phy.u_link.u_dec.u_chn.rst_n'
                or b['native_clock_root'] != 'pma_rck'):
            raise ValueError('native release unproved target or root')
        row = W['parts'][b['part']]['native_release'][b['target']]
        if row['native_clock_root'] != b['native_clock_root']:
            raise ValueError('native release actual clock-root mismatch')
        row.update(status='QUALIFIED_CONDITIONAL', core_cycle_release=None,
                   min_recovered_edges_after_authorities_high=68,
                   guard_recovered_edges=66, leaf_resynchronizer_edges=2,
                   conditions=['delivered reset high', 'PMA lock high', 'PMA recovered clock running'],
                   qualification='measured local reset contract; no finite core-cycle deadline while recovered clock is stopped')
    W['release_qualification'] = dict(verdict='QUALIFIED_CONDITIONAL', native_targets=bindings,
        receipt_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        reason='OWNER 11-02: local reset held >=64 recovered-clock edges after restart; no mission latency or core-cycle deadline inferred')
    W['note'] += ' Native PHY reset is conditionally qualified in recovered-clock edges; core-cycle release remains unknown.'
    return W
