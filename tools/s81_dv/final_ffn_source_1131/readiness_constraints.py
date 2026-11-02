#!/usr/bin/env python3
"""Compile conditional source readiness from measured selected-leaf read edges.

No frame epochs or production burst assignment are chosen by this tool.
"""
import argparse
import json
import re
from pathlib import Path


def measured_reads(receipt):
    if receipt['clock_ps'] != 833:
        raise ValueError('selected native receipt must use 833 ps')
    if receipt['status'] != 'PASS_SELECTED_NATIVE64_READ_LEASE':
        raise ValueError('selected native read lease did not pass')
    safe = receipt['safe']
    if not safe['qualified'] or any(safe[k] for k in ('collisions', 'stale', 'errors')):
        raise ValueError('unsafe native read lease')
    if [e - safe['rdreg'] for e in safe['native_publication_edges']] != list(range(5, 13)):
        raise ValueError('native publication timing differs from selected profile')
    if [e - safe['rdreg'] for e in safe['public_publication_edges']] != list(range(6, 14)):
        raise ValueError('public publication timing differs from selected profile')
    offsets = []
    for i in range(8):
        events = [e for e in safe['read_events'] if e['row'] == 112 + i]
        if sorted(e['bank'] for e in events) != [0, 1]:
            raise ValueError('both native SRAM banks must be measured')
        delta = {e['edge'] - safe['rdreg'] for e in events}
        if delta != {3 + i}:
            raise ValueError('read timing differs from selected native profile')
        offsets.append(delta.pop())
    return offsets


def replay_log(text, rdreg, offsets):
    """Strictly precede each bank read with all four word commits for that row."""
    writes = {}
    for bank, edge, row, mask in re.findall(
            r'^WRITE bank(\d) edge(\d+) row(\d+) mask([0-9a-f]+)$', text, re.M):
        value = int(mask, 16)
        for word in range(4):
            if value & (0xffffffff << (word * 32)):
                writes[int(bank), int(row), word] = int(edge)
    if len(writes) != 64:
        raise ValueError('need all 64 measured word commits')
    violations = []
    required_cv = max(commit + 1 - offsets[row - 112]
                      for (bank, row, word), commit in writes.items())
    for (bank, row, word), commit in writes.items():
        read = rdreg + offsets[row - 112]
        if commit >= read:
            violations.append(dict(bank=bank, row=row, word=word,
                                   commit_edge=commit, read_edge=read))
    return dict(minimum_registered_CV=required_cv,
                tested_registered_CV=rdreg, violations=violations,
                safe=not violations)


def compile_constraints(join, receipt):
    offsets = measured_reads(receipt)
    pairs = []
    for pair in join['RD_pairs']:
        alternatives = []
        for i, read_offset in enumerate(offsets):
            terms = []
            for word in pair['word_events']:
                # Integer edges: CV + offset > commit, excluding same-edge R/W.
                terms.append(dict(CAP_word_address=word['CAP_word_address'],
                                  source_epoch=word['unknown_epoch'],
                                  minimum_CV_relative_to_source_epoch=
                                  word['composed_commit_edge_n'] + 1 - read_offset))
            alternatives.append(dict(conditional_burst_pair_index=i,
                                     actual_SRAM_read_offset_from_CV=read_offset,
                                     native_LO_offset_from_CV=5 + i,
                                     public_LO_offset_from_CV=6 + i,
                                     all_word_lower_bounds=terms))
        pairs.append(dict(ledger_i=pair['ledger_i'],
                          source_row_pair=pair['source_row_pair'],
                          destination_row_pair=pair['destination_row_pair'],
                          production_burst_pair_index=None,
                          production_registered_CV=None,
                          alternatives=alternatives))
    return dict(status='PASS_CONDITIONAL_SELECTED_NATIVE_READINESS_CONSTRAINTS',
                clock_ps=833, inequality='registered_CV + read_offset > every source-word commit',
                source_pairs=pairs,
                physical_same_address_read_write_qualified=False,
                actual_mission_capture_qualified=False, global_leases_qualified=False,
                production_burst_binding_qualified=False, added_rtl_cycles=0,
                full_token=False,
                holds=join['holds'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('join', 'native', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    result = compile_constraints(json.loads(a.join.read_text()), json.loads(a.native.read_text()))
    with a.out.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(result['status'])


if __name__ == '__main__':
    main()
