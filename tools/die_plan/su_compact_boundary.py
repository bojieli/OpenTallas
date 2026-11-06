#!/usr/bin/env python3
"""Prepare a private SU source cohort with the VI reader kept inside each bank/lane cut.

This pass removes unobserved bank word4 and the unused upper six write-address bits.
It does not substitute a physical child or change arithmetic/clock parameters.
"""
import argparse
import hashlib
import json
from pathlib import Path

REPLACEMENTS = {
    'wire [32*24-1:0] vi_addr,vm_waddr,kv_waddr;': 'wire [32*24-1:0] vi_addr; wire [32*18-1:0] vm_waddr,kv_waddr; wire [32*6-1:0] vm_waddr_unused_high,kv_waddr_unused_high;',
    'wire [23:0] la=vm_we[n]?vm_waddr[n*24+:24]:kv_waddr[n*24+:24];': 'wire [17:0] la=vm_we[n]?vm_waddr[n*18+:18]:kv_waddr[n*18+:18];',
    'wire [32*192-1:0] bank_q;': 'wire [32*160-1:0] bank_q;',
    'assign bank_q[n*192+:192]=q;': 'assign bank_q[n*160+:160]={q[191:160],q[127:0]};',
    'bank_q[n*192+p*32+:32]': 'bank_q[n*160+p*32+:32]',
    'bank_q[(8*h+16*hi+kk)*192+5*32+:32]': 'bank_q[(8*h+16*hi+kk)*160+4*32+:32]',
}

def compact_source(text):
    for old, new in REPLACEMENTS.items():
        if text.count(old) != 1:
            raise ValueError(f'Expected exactly one native SU boundary expression: {old}')
        text = text.replace(old, new)
    for name in ['vm_waddr', 'kv_waddr']:
        old = f'.{name}({name}[n*24+:24])'
        new = f'.{name}({{{name}_unused_high[n*6+:6],{name}[n*18+:18]}})'
        if text.count(old) != 2:
            raise ValueError(f'Expected pinreg and plain native address outputs: {name}')
        text = text.replace(old, new)
    return text


def compact_compose(config):
    changed = []
    for core in config['cores']:
        port = core.get('ports', {}).get('bank_read_data')
        if not port or port.get('dir') != 'output':
            continue
        bits = port['bits']
        # Only the explicit native six-reader ABI can be pruned. Every bit must
        # name one bank read_data bit; a different representation is unsupported.
        refs = [row[0] for row in bits if isinstance(row, list) and len(row) == 1]
        if len(refs) != len(bits) or any(r.get('port') != 'read_data' for r in refs):
            raise ValueError(f'Unsupported bank_read_data mapping: {core["inst"]}')
        members = list(dict.fromkeys(r['member'] for r in refs))
        if len(bits) != len(members) * 192:
            continue  # Already a narrower cut; preserve its existing ABI.
        for m in members:
            if [r['bit'] for r in refs if r['member'] == m] != list(range(192)):
                raise ValueError(f'Noncanonical six-reader mapping: {core["inst"]}/{m}')
        port['bits'] = [row for row in bits if not 128 <= row[0]['bit'] < 160]
        original = core['module']
        core['module'] = original + '__p17_boundary'
        address_changes = {}
        for address in ['lane_vm_waddr', 'lane_kv_waddr']:
            ap = core['ports'].get(address)
            if not ap:
                continue
            ab = ap['bits']
            if any(not isinstance(row, list) or len(row) != 1 or row[0].get('port') != address[5:] for row in ab):
                raise ValueError(f'Unsupported write address mapping: {core["inst"]}/{address}')
            if len(ab) != len(members) * 24:
                raise ValueError(f'Noncanonical write address width: {core["inst"]}/{address}')
            ap['bits'] = [row for row in ab if row[0]['bit'] < 18]
            address_changes[address] = [len(ab),len(ap['bits'])]
        changed.append({'instance': core['inst'], 'native_module': original,
                        'module': core['module'], 'before_bits': len(bits),
                        'after_bits': len(port['bits']), 'write_addresses': address_changes})
    if not changed:
        raise ValueError('No explicit native six-reader SU cuts found')
    return changed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--compose', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    source = a.source.read_bytes()
    compose = a.compose.read_bytes()
    transformed = compact_source(source.decode())
    config = json.loads(compose)
    changes = compact_compose(config)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / a.source.name).write_text(transformed)
    (a.out / 'compose_vi_internal.json').write_text(json.dumps(config, indent=1)+'\n')
    manifest = {'status': 'SOURCE_PREPARATION_ONLY', 'physical_child_substitution': False,
                'source': str(a.source), 'source_sha256': hashlib.sha256(source).hexdigest(),
                'compose': str(a.compose), 'compose_sha256': hashlib.sha256(compose).hexdigest(),
                'changes': changes, 'added_cycles': 0,
                'retained_native_local_feedback': 'bank read word4 to paired lane vi_q',
                'controller_words': [0, 1, 2, 3, 5],
                'write_address_observation': 'Bank row bits17:16/13:7 and id checks15:14/6:0 only; upper bits23:18 remain unobserved native outputs',
                'next': 'Reelaborate this explicit source/compose cohort before signed child composition; do not route this preparation artifact.'}
    (a.out / 'su_source_profile.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Prepared {len(changes)} explicit VI-internal cuts; no child substituted')

if __name__ == '__main__':
    main()
