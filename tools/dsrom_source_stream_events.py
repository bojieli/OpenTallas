#!/usr/bin/env python3
"""Materialize LAT8 offered activation words from the resident PAR2 plans.

This is a static source schedule, not an accepted hardware event trace. The
spine's s_ok, provider acknowledgments and return fences remain separate gates.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path
import dsrom_full_owner_compiler as C
import dsrom_owner_cfg_interface_export as E

ROOT = Path(__file__).resolve().parents[1]


def stream(matrix):
    fmt = matrix['format']
    load = collections.Counter()
    required = collections.defaultdict(set)
    for si, pair, first, count, stride, base, words in matrix['plans']:
        e0, size = matrix['segments'][si]
        u0, u1 = C.S.unit_range(fmt, e0, size)
        for q, start in enumerate(range(u0, u1, 8)):
            units = list(range(start, min(u1, start + 8)))
            required[q].update(units)
            load[pair, q] += count * sum(len(C.S.unit_halves(fmt, e0, size, u)) for u in units)
    beats = []
    rounds = []
    for q, units in sorted(required.items()):
        units = sorted(units)
        groups = [units[i:i+4] for i in range(0, len(units), 4)] if fmt == 'bf16' else [[u] for u in units]
        length = max(8, len(groups), max(v for (p, qq), v in load.items() if qq == q))
        slots = {i * length // len(groups): g for i, g in enumerate(groups)}
        rounds.append(dict(q=q, cycles_per_block=length, units=units,
                           max_pair_reads_per_block=max(v for (p, qq), v in load.items() if qq == q),
                           shards=[dict(shard=s,
                                        max_pair_reads_per_block=max([v for (p, qq), v in load.items() if qq == q and p//2048 == s]+[0]),
                                        total_pair_reads_per_block=sum(v for (p, qq), v in load.items() if qq == q and p//2048 == s))
                                   for s in (0,1)]))
        for block in range(8):
            for slot in range(length):
                group = slots.get(slot, [])
                word = 0
                if group and fmt == 'bf16':
                    if max(group) >= 256:
                        raise ValueError('BF16 unit exceeds source eight-bit field')
                    word = 1 | block << 1
                    for lane, u in enumerate(group):
                        word |= 1 << (4+lane) | u << (8+8*lane)
                    need = (max(group)+1)*128
                elif group:
                    u = group[0]
                    if u >= 256:
                        raise ValueError('quantized unit exceeds source eight-bit field')
                    valid = sum(1 << h for h in (0, 1) if 2*u+h < matrix['K']//256)
                    word = 1 | u << 1 | block << 9 | valid << 12
                    need = (2*u + (1 if valid & 2 else 0))*256 + (block+1)*32
                else:
                    need = 0
                beats.append(dict(offered_index=len(beats), q=q, block=block,
                                  word48=word, units=group, required_loaded_elements=need))
    if len(beats) != matrix['issue_cycles_LAT8_condition']:
        raise ValueError('stream length differs from owner compiler LAT8 accounting')
    if 8*sum(sum(s['total_pair_reads_per_block'] for s in r['shards']) for r in rounds) != sum(p[3]*p[6] for p in matrix['plans']):
        raise ValueError('offered pair read conservation differs from resident plans')
    return rounds, beats


def generate(out):
    if out.exists():
        raise ValueError('preserve prior record; use fresh output')
    selected = {}
    count = 0
    for ordinal, m in enumerate(C.readrows(E.JOURNAL/'assignments.jsonl.gz')):
        count += 1
        fmt = m['format']
        selected.setdefault('first_'+fmt, (ordinal, m))
        key = 'max_issue_'+fmt
        if key not in selected or m['issue_cycles_LAT8_condition'] > selected[key][1]['issue_cycles_LAT8_condition']:
            selected[key] = ordinal, m
        if (m['layer'], m['alias']) == (1, 'engram.wkv'):
            selected['L1_engram_wkv'] = ordinal, m
    if count != 46509:
        raise ValueError('resident phase inventory changed')
    out.mkdir(parents=True)
    profiles = []
    for name, (ordinal, m) in sorted(selected.items()):
        rounds, beats = stream(m)
        file = name+'.json'
        record = dict(name=name, matrix_journal_ordinal=ordinal, layer=m['layer'], alias=m['alias'],
                      stage=m['stage'], format=m['format'], K=m['K'], rows=m['rows'],
                      rounds=rounds, offered_beats=beats,
                      config_word_count=25, config_source_last_capture_edge=26,
                      config_source_safe_GO_edge=27,
                      cfg_edges_relative_to_pair_cfg_command=True,
                      activation_word_indices_are_not_absolute_cycles=True,
                      physical_provider_accepted_events=False, consumer_deadlines_bound=False,
                      original_spine_completion='rows_left == 0 && !sm_run && !ld_run',
                      pair_busy_alone_is_not_completion=True)
        (out/file).write_text(json.dumps(record, indent=2, sort_keys=True)+'\n')
        profiles.append(dict(name=name, file=file, offered_words=len(beats),
                             valid_words=sum(bool(b['word48'] & 1) for b in beats)))
    sources = ['tools/dsrom_source_stream_events.py', 'tools/dsrom_full_owner_compiler.py',
               'tools/v41_die_images.py', 'tools/v41_rom_ksplit_bankmap.py',
               'rtl/v41die/ot_v41_spine_w17w10.sv', 'rtl/v41die/ot_v41_pair_w17w10.sv',
               str((E.JOURNAL/'assignments.jsonl.gz').relative_to(ROOT))]
    summary = dict(schema='opentallas.dsrom.offered-source-stream.v1', scanned_resident_phases=count,
                   recurrence_cycles=8, profiles=profiles, accepted_service_calendar=False,
                   physical_or_numerical_adoption=False,
                   source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})
    (out/'model.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    print(json.dumps(generate(parser.parse_args().out), sort_keys=True))
