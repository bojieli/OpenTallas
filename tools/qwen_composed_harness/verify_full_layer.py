#!/usr/bin/env python3
"""Compare executed results only. This tool never supplies hardware inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(oracle, actual):
    oracle_report = json.loads((oracle / 'oracle.json').read_text())
    if oracle_report.get('collective_reference_profile') != 'production_tp8_two_level':
        raise ValueError('acceptance requires production two-level TP8 reference')
    ranks = []
    for rank in range(8):
        source = oracle / f'die{rank}'
        vm_path = actual / f'rank{rank}_VM.hex'
        expected_path = source / 'candidate_pc23_vm.npz'
        with np.load(expected_path) as expected:
            values = np.array([int(x, 16) for x in vm_path.read_text().split()], dtype=np.uint32)
            bits = expected['vm_bits']
            mask = expected['defined_effect_mask']
            if values.shape != bits.shape:
                raise ValueError(f'rank {rank}: actual VM dimensions differ')
            mismatch = np.flatnonzero(mask & (values != bits))
            vm_words = int(mask.sum())
        boundaries = []
        for segment, pc in enumerate((12, 20, 23)):
            boundary = actual / f'rank{rank}_segment{segment}_VM.hex'
            reference = source / f'candidate_pc{pc}_vm.npz'
            with np.load(reference) as expected:
                boundary_bits = np.array([int(x, 16) for x in boundary.read_text().split()], dtype=np.uint32)
                if boundary_bits.shape != expected['vm_bits'].shape:
                    raise ValueError('actual segment boundary VM dimensions differ')
                errors = np.flatnonzero(expected['defined_effect_mask'] & (boundary_bits != expected['vm_bits']))
            boundaries.append({'segment': segment, 'source_candidate_pc': pc,
                               'errors': len(errors), 'first_error_addresses': errors[:16].tolist(),
                               'actual_sha256': sha(boundary), 'expected_sha256': sha(reference)})
        expected_kv = {}
        expected_kv_owner = {}
        for pc in (3, 8, 10):
            with np.load(source / f'candidate_pc{pc}_KV_commits.npz') as commits:
                # Exact stored FP32 represents the already-rounded FP8 value.
                addresses = commits['element_addresses'].reshape(-1)
                payload_name = next(k for k in commits.files if k != 'element_addresses')
                for address, value in zip(addresses, commits[payload_name].reshape(-1)):
                    address, value = int(address), int(value)
                    if address in expected_kv:
                        raise ValueError('overlapping expected current KV writes')
                    expected_kv[address] = value
                    expected_kv_owner[address] = pc
        observed_kv = {}
        for line in (actual / f'rank{rank}_KV.txt').read_text().splitlines():
            address, value, edge, owner_pc = line.split()
            address = int(address)
            owner_pc = int(owner_pc)
            if owner_pc not in (3, 8, 10):
                raise ValueError('actual KV write has invalid accepted SU owner')
            if expected_kv_owner.get(address) != owner_pc:
                raise ValueError('actual KV write address differs from accepted SU operation')
            if address in observed_kv:
                raise ValueError(f'rank {rank}: duplicate actual KV write {address}')
            observed_kv[address] = int(value, 16)
        kv_errors = sum(observed_kv.get(a) != v for a, v in expected_kv.items()) + len(observed_kv.keys() - expected_kv.keys())
        accepted = [tuple(map(int, l.split())) for l in (actual / f'rank{rank}_accepted.txt').read_text().splitlines()]
        expected_pcs = [pc for pc in range(25) if pc not in (13, 21, 24)]
        if [pc for pc, unit, edge in accepted] != expected_pcs:
            raise ValueError(f'rank {rank}: instruction order differs from actual 25-word image')
        operation_counts = {}
        operation_errors = []
        operation_reference = {}
        for line in (actual / f'rank{rank}_operation_commits.txt').read_text().splitlines():
            pc, address, value, edge, port = line.split()
            pc, address, value = int(pc), int(address), int(value, 16)
            if pc not in expected_pcs:
                raise ValueError('actual VM commit has invalid accepted provider owner')
            if pc not in operation_reference:
                with np.load(source / f'candidate_pc{pc}_vm.npz') as expected:
                    operation_reference[pc] = (expected['vm_bits'].copy(), expected['defined_effect_mask'].copy())
            bits, mask = operation_reference[pc]
            if not 0 <= address < len(bits):
                raise ValueError('actual operation commit is outside VM')
            operation_counts[pc] = operation_counts.get(pc, 0) + 1
            if mask[address] and bits[address] != value:
                operation_errors.append({'pc': pc, 'address': address, 'actual': value,
                                         'expected': int(bits[address]), 'edge': int(edge), 'port': port})
        expected_vm_pcs = set(expected_pcs) - {3, 8, 10}
        if set(operation_counts) != expected_vm_pcs:
            raise ValueError(f'rank {rank}: missing actual operation commits {expected_vm_pcs-set(operation_counts)}')
        ranks.append({'rank': rank, 'defined_VM_words': vm_words,
                      'VM_errors': len(mismatch), 'first_VM_error_addresses': mismatch[:16].tolist(),
                      'expected_KV_commits': len(expected_kv), 'actual_KV_commits': len(observed_kv),
                      'KV_errors': kv_errors, 'actual_VM_sha256': sha(vm_path),
                      'quiescent_segment_boundaries': boundaries,
                      'per_operation_actual_commits': operation_counts,
                      'per_operation_commit_errors': len(operation_errors),
                      'first_per_operation_errors': operation_errors[:16],
                      'expected_VM_sha256': sha(expected_path)})
    collectives = []
    for segment, pc in enumerate((12, 20)):
        # Independent observer: exact binary32 pair folds, then package order.
        # These values never enter the executable or collector input paths.
        partials = []
        for rank in range(8):
            with np.load(oracle / f'die{rank}' / f'candidate_pc{pc}_vm.npz') as expected:
                partials.append(expected['vm_bits'][:4096].view(np.float32).copy())
        def add(a, b):
            value = np.add(a, b, dtype=np.float32)
            return np.where(value == 0, np.float32(0), value).astype(np.float32)
        packages = [add(partials[p], partials[p + 4]) for p in range(4)]
        folded = packages[0]
        for package in packages[1:]:
            folded = add(folded, package)
        folded = folded.view(np.uint32)
        errors = 0
        for rank in range(8):
            path = actual / f'collective{segment}' / 'actual' / f'rank{rank}.hex'
            result = []
            for word in path.read_text().split():
                if len(word) != 128:
                    raise ValueError('actual collective output word width differs')
                result.extend(int(word[128-8*(lane+1):128-8*lane], 16) for lane in range(16))
            if len(result) != 4096:
                raise ValueError('actual collective output count differs')
            errors += int(np.count_nonzero(np.array(result, dtype=np.uint32) != folded))
        collectives.append({'segment': segment, 'actual_returned_words': 32768, 'errors': errors})
    report = {'scope': 'ACTUAL_LAYER0_DEFINED_EFFECT_COMPARISON_ONLY', 'ranks': ranks,
              'actual_collective_returns': collectives,
              'ok': all(r['VM_errors'] == r['KV_errors'] == r['per_operation_commit_errors'] == 0 and
                        all(b['errors'] == 0 for b in r['quiescent_segment_boundaries']) for r in ranks)
                    and all(c['errors'] == 0 for c in collectives),
              'oracle_receipt_sha256': sha(oracle / 'oracle.json')}
    (actual / 'defined_effect_receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return report['ok']

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--oracle', type=Path, required=True)
    p.add_argument('--actual', type=Path, required=True)
    a = p.parse_args()
    raise SystemExit(0 if verify(a.oracle, a.actual) else 1)
