#!/usr/bin/env python3
"""Compare executed results only. This tool never supplies hardware inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(oracle, actual, catalog_path=None, fields_path=None, grant_path=None):
    oracle_report = json.loads((oracle / 'oracle.json').read_text())
    if grant_path is None:
        raise ValueError('native acceptance requires actual central held grant receipt')
    grant = json.loads(grant_path.read_text())
    if not grant['delivered'] or not grant['busy'] or grant['generation'] != 2 or grant['position'] != oracle_report['position']:
        raise ValueError('actual central grant state/position differs')
    expected_q_tag = ((grant['epoch'] << 43) | ((oracle_report.get('payload_layer', 0) + 1) << 37) |
                      (grant['token'] << 19) | (grant['position'] << 6))
    if oracle_report.get('collective_reference_profile') != 'production_tp8_two_level':
        raise ValueError('acceptance requires production two-level TP8 reference')
    sidecar = json.loads(catalog_path.read_text()) if catalog_path else None
    if fields_path is None:
        raise ValueError('acceptance requires independently resolved accepted SU field expectations')
    resolved_fields = json.loads(fields_path.read_text())
    if resolved_fields['position'] != oracle_report['position']:
        raise ValueError('resolved field catalog position differs')
    if resolved_fields['decoder_sha256'] != oracle_report['source_sha256']['tools/hdc_isa.py']:
        raise ValueError('resolved field catalog decoder pin differs from arithmetic source')
    if sidecar and (sidecar['layer'] != oracle_report.get('payload_layer', 0) or
                    sidecar['position'] != oracle_report['position']):
        raise ValueError('destination sidecar belongs to a different layer/position')
    ranks = []
    for rank in range(8):
        source = oracle / f'die{rank}'
        vm_path = actual / f'rank{rank}_VM.hex'
        expected_path = source / 'candidate_pc23_vm.npz'
        if sha(expected_path) != oracle_report['ranks'][str(rank)]['effects']['23']['full_VM_sha256']:
            raise ValueError('final VM reference artifact digest differs')
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
            if sha(reference) != oracle_report['ranks'][str(rank)]['effects'][str(pc)]['full_VM_sha256']:
                raise ValueError('segment-boundary reference artifact digest differs')
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
            if sha(source / f'candidate_pc{pc}_KV_commits.npz') != oracle_report['ranks'][str(rank)]['effects'][str(pc)]['KV_commit_sha256']:
                raise ValueError('current KV reference artifact digest differs')
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
        observed_destinations = {}
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
            observed_destinations.setdefault((owner_pc, 'KV'), []).append(address)
        kv_errors = sum(observed_kv.get(a) != v for a, v in expected_kv.items()) + len(observed_kv.keys() - expected_kv.keys())
        accepted = [tuple(map(int, l.split())) for l in (actual / f'rank{rank}_accepted.txt').read_text().splitlines()]
        expected_pcs = [pc for pc in range(25) if pc not in (13, 21, 24)]
        if [pc for pc, unit, edge in accepted] != expected_pcs:
            raise ValueError(f'rank {rank}: instruction order differs from actual 25-word image')
        source_fields = resolved_fields['ranks'][str(rank)]
        if source_fields['program_sha256'] != oracle_report['ranks'][str(rank)]['lowered_program_sha256']:
            raise ValueError('resolved fields belong to a different input program')
        raw_lines = (actual / f'rank{rank}_accepted_actual_words.txt').read_text().splitlines()
        if len(raw_lines) != 25:
            raise ValueError('actual FIFO-to-NEXT witness must cover all 25 accepted/END instructions')
        source_words = source_fields['source_program_words']
        for expected_pc, line in enumerate(raw_lines):
            pc, unit, edge, end, word = line.split()
            pc, unit, edge, end = map(int, (pc, unit, edge, end))
            if (pc != expected_pc or word.lower() != source_words[pc] or
                unit != (int(word, 16) & 3) or end != int(pc in (13, 21, 24))):
                raise ValueError(f'rank {rank}: actual accepted FIFO-to-NEXT word/ownership differs at PC{expected_pc}')
        q_observations = [line.split() for line in (actual / f'rank{rank}_QVM_tags.txt').read_text().splitlines()]
        seen_q = set()
        for edge, tag, epoch, chunk, response in q_observations:
            identity = (int(chunk), int(response))
            if (int(tag, 16) != expected_q_tag or int(epoch) != grant['epoch'] or
                identity in seen_q or identity[0] not in range(8) or identity[1] not in (0, 1)):
                raise ValueError('actual accepted Q request/reply TAG59 differs or repeats')
            seen_q.add(identity)
        if seen_q != {(chunk, direction) for chunk in range(8) for direction in (0, 1)}:
            raise ValueError('missing actual accepted Q request/reply TAG59 observations')
        attn_events = [line.split() for line in (actual / f'rank{rank}_ATTN_tags.txt').read_text().splitlines()]
        seen_attn = {}
        for edge, tag, address, beat, ack in attn_events:
            edge, address, beat, ack = map(int, (edge, address, beat, ack))
            identity = (beat, ack)
            if (int(tag, 16) != expected_q_tag or address != 50672 + 16 * beat or
                beat not in range(32) or ack not in (0, 1) or identity in seen_attn):
                raise ValueError('actual ATT write/delayed ACK TAG59/address differs or repeats')
            seen_attn[identity] = edge
        if set(seen_attn) != {(beat, direction) for beat in range(32) for direction in (0, 1)}:
            raise ValueError('missing actual ATT write/delayed ACK TAG59 observations')
        if any(seen_attn[(beat, 1)] <= seen_attn[(beat, 0)] for beat in range(32)):
            raise ValueError('ATT ACK preceded its actual addressed write/store edge')
        observed_fields = {}
        for line in (actual / f'rank{rank}_accepted_SU_descriptors.txt').read_text().splitlines():
            parts = list(map(int, line.split()))
            if len(parts) != 2 + len(resolved_fields['keys']):
                raise ValueError('accepted SU descriptor observation width differs')
            pc, edge = parts[:2]
            if str(pc) in observed_fields:
                raise ValueError('duplicate accepted SU descriptor observation')
            observed_fields[str(pc)] = dict(zip(resolved_fields['keys'], parts[2:]))
        if observed_fields != source_fields['resolved_SU_fields']:
            raise ValueError(f'rank {rank}: actually accepted resolved SU fields differ from pinned source/dynamics')
        operation_counts = {}
        operation_errors = []
        operation_reference = {}
        for line in (actual / f'rank{rank}_operation_commits.txt').read_text().splitlines():
            pc, address, value, edge, port = line.split()
            pc, address, value = int(pc), int(address), int(value, 16)
            if pc not in expected_pcs:
                raise ValueError('actual VM commit has invalid accepted provider owner')
            if pc not in operation_reference:
                if sha(source / f'candidate_pc{pc}_vm.npz') != oracle_report['ranks'][str(rank)]['effects'][str(pc)]['full_VM_sha256']:
                    raise ValueError('operation reference artifact digest differs')
                with np.load(source / f'candidate_pc{pc}_vm.npz') as expected:
                    operation_reference[pc] = (expected['vm_bits'].copy(), expected['defined_effect_mask'].copy())
            bits, mask = operation_reference[pc]
            if not 0 <= address < len(bits):
                raise ValueError('actual operation commit is outside VM')
            operation_counts[pc] = operation_counts.get(pc, 0) + 1
            observed_destinations.setdefault((pc, port), []).append(address)
            if mask[address] and bits[address] != value:
                operation_errors.append({'pc': pc, 'address': address, 'actual': value,
                                         'expected': int(bits[address]), 'edge': int(edge), 'port': port})
        expected_vm_pcs = set(expected_pcs) - {3, 8, 10}
        if set(operation_counts) != expected_vm_pcs:
            raise ValueError(f'rank {rank}: missing actual operation commits {expected_vm_pcs-set(operation_counts)}')
        for pc, count in ((1, 768), (12, 4096), (16, 3072), (20, 4096), (11, 512)):
            if operation_counts.get(pc) != count:
                raise ValueError(f'rank {rank}: exact output count differs for provider operation {pc}')
        catalog = oracle_report['ranks'][str(rank)].get('operation_destinations')
        if sidecar:
            side_rank = sidecar['ranks'][str(rank)]
            if side_rank['actual_image_sha256'] != oracle_report['ranks'][str(rank)]['image_sha256'] or side_rank['candidate_program_sha256'] != oracle_report['ranks'][str(rank)]['lowered_program_sha256']:
                raise ValueError('destination sidecar source image/program digests differ')
            catalog = side_rank['operations']
        if not catalog:
            raise ValueError('acceptance requires independent complete destination catalogs')
        expected_destinations = {(int(pc), port): addresses for pc, ports in catalog.items()
                                 for port, addresses in ports.items() if addresses}
        if observed_destinations.keys() != expected_destinations.keys():
            raise ValueError('actual committed provider/operation set differs from complete catalog')
        for identity, addresses in observed_destinations.items():
            if sorted(addresses) != sorted(expected_destinations[identity]):
                raise ValueError(f'rank {rank}: missing/extra/duplicate commits for operation/port {identity}')
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
        # Independent production oracle returns are observer-only. Actual
        # collector inputs remain the hardware-produced rank partials.
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
            expected_path = oracle / f'die{rank}' / f'collective{segment}_return.hex'
            expected = np.array([int(x, 16) for x in expected_path.read_text().split()], dtype=np.uint32)
            if expected.size != 4096:
                raise ValueError('independent collective return dimensions differ')
            errors += int(np.count_nonzero(np.array(result, dtype=np.uint32) != expected))
        collectives.append({'segment': segment, 'actual_returned_words': 32768, 'errors': errors})
    report = {'scope': 'ACTUAL_LAYER0_DEFINED_EFFECT_COMPARISON_ONLY', 'ranks': ranks,
              'actual_collective_returns': collectives,
              'ok': all(r['VM_errors'] == r['KV_errors'] == r['per_operation_commit_errors'] == 0 and
                        all(b['errors'] == 0 for b in r['quiescent_segment_boundaries']) for r in ranks)
                    and all(c['errors'] == 0 for c in collectives),
              'oracle_receipt_sha256': sha(oracle / 'oracle.json')}
    report['explicit_catalog_sha256'] = sha(catalog_path) if catalog_path else None
    report['resolved_field_catalog_sha256'] = sha(fields_path)
    report['actual_held_grant_receipt_sha256'] = sha(grant_path)
    report['actual_QVM_request_and_return_TAG59_observed'] = True
    report['actual_ATT_write_and_delayed_ACK_TAG59_observed'] = True
    report['actual_accepted_FIFO_to_NEXT_1024_bits_proved'] = True
    report['accepted_raw_IB379_context16_version32_proved'] = False
    (actual / 'defined_effect_receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return report['ok']

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--oracle', type=Path, required=True)
    p.add_argument('--actual', type=Path, required=True)
    p.add_argument('--catalog', type=Path)
    p.add_argument('--fields', type=Path, required=True)
    p.add_argument('--grant', type=Path, required=True)
    a = p.parse_args()
    raise SystemExit(0 if verify(a.oracle, a.actual, a.catalog, a.fields, a.grant) else 1)
