#!/usr/bin/env python3
"""Retain actual publication metadata and produced KV hashes, without replay."""
import argparse
import hashlib
import json
from pathlib import Path
from qwen_hbm_complete_verify_terminal import load, verify

def capture(archive, repo=None):
    archive = Path(archive)
    verdict = verify(archive, repo)
    execution = load(archive, 'token1_execution.json.gz')
    hashes = load(archive, 'instruction_output_hashes.json.gz')
    outputs = {(r['position'], r['register']): r for r in hashes}
    pending, published = {}, []
    for event in execution['memory_events']:
        if event['event'] == 'write_accepted_not_published':
            pending[event['tag']] = event
        elif event['event'] == 'software_backing_commit_and_publication':
            write = pending.pop(event['tag'])
            position, layer, die = (write[k] for k in ('position', 'layer', 'die'))
            row = dict(position=position, layer=layer, die=die,
                       publication_tag=event['tag'], committed_bytes=write['bytes'])
            for kind, register in [('K', f'L{layer}.d{die}.kr'),
                                   ('V', f'L{layer}.d{die}.v')]:
                produced = outputs[position, register]
                if produced['shape'] != [4, 128]:
                    raise ValueError('produced KV shape')
                row[kind] = dict(register=register, shape=produced['shape'],
                                 produced_FP32_sha256=produced['sha256'])
            published.append(row)
    if pending or len(published) != 144:
        raise ValueError('publication coverage')
    return dict(schema='Qwen_actual_two_token_KV_metadata_r1',
                worker_source_commit='defc45332c52a173d47f882595ddd78c4ce22fde',
                archive_receipt_sha256=hashlib.sha256((archive/'receipt.json').read_bytes()).hexdigest(),
                actual_returncode=verdict['actual_returncode'],
                scope='Original worker events and produced pre-codec FP32 hashes; no execution replay',
                publications=published, pending_writes=0, outstanding_reader_leases=0,
                committed_payload_bytes=sum(r['committed_bytes'] for r in published),
                encoded_KV_payload_dump_retained=False,
                limitation='Original worker did not dump encoded KV bytes; metadata and hashes cannot restore their values.',
                actual_hardware_memory_provider=False, token_cycles=None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--repo')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(capture(args.archive, args.repo), indent=2)+'\n')
