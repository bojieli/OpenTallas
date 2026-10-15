#!/usr/bin/env python3
"""Compile canonical BF pair issue identities from plans, CFG25 and native stream.

No RTL observation, numerical output, dynamic availability or synthetic weight
is accepted. The external programme offset is a declared ingress contract.
"""
import argparse
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import dsrom_full_owner_compiler as compiler
import dsrom_s81_target_field_controls as controls
import v41_rom_ksplit_bankmap as bankmap


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def first_bf(base):
    expected = {
        'matrix_map.jsonl.gz': '985a9ee7ea26d2a7bb1aebadc5151252836eacf8181e8794b1ef6d7819db0326',
        'stage_map.json': '47ea9eb0ba0b404f629a4bc758d28d8ac1fe28dcb31de3e5816517fa1d097815',
        'inventory.json': '0b8d8f6fddf7a427941b7a235aeb80e0ee370c51cafddba6427fa61d3ff99480'}
    for name, digest in expected.items():
        if sha(base/name) != digest:
            raise ValueError('canonical source pin changed: '+name)
    phases = {}
    with gzip.open(base/'matrix_map.jsonl.gz', 'rt') as stream:
        for line in stream:
            matrix = json.loads(line)
            stage = matrix['stage']; phase = phases.get(stage, 0)
            phases[stage] = phase+1
            if matrix['format'] == 'bf16':
                return matrix, phase, expected
    raise ValueError('canonical BF source absent')


def generate(base, output, *, issue_offset, fp32_output):
    matrix, phase, pins = first_bf(base)
    # First plan in authoritative allocator order. Never choose a smaller pair.
    pair = matrix['plans'][0][1]
    runs = [r for r in matrix['plans'] if r[1] == pair]
    if (matrix['stage'], phase, pair, matrix['K'], runs) != (0, 4, 13, 4096, [[0, 13, 0, 1, 128, 80, 256]]):
        raise ValueError('first canonical BF pair shape changed; refuse implicit schedule extension')
    cfg = compiler.phase_cfg(matrix, pair)
    segments = []
    for si, _, first, count, stride, start, words in runs:
        e0, elems = matrix['segments'][si]
        for j in range(count):
            segments.append(dict(fmt='bf16', e0=e0, elems=elems,
                                 row=first+j*stride, tensor=matrix['tensor']))
    order = bankmap.element_order(segments)
    phrom, stream, emitter_sha = controls.native_stream(matrix, fp32_output=fp32_output)
    # Canonical stream delivers four units per beat. Derive arrival slots from
    # its immutable words and pair class membership, rather than a trace.
    arrivals = {}
    for edge, word in enumerate(stream):
        if not word & 1:
            continue
        block = (word >> 1) & 7
        for lane in range(4):
            if word & (1 << (4+lane)):
                unit = (word >> (8+8*lane)) & 255
                if (unit, block) in arrivals:
                    raise ValueError('ambiguous stream operand identity')
                arrivals[unit, block] = edge
    records = []; last_chain = {}; next_edge = issue_offset
    last_round = None; chain = 0
    for index, (slot, unit, block, half) in enumerate(order):
        sg = segments[slot]
        u0, _ = bankmap.unit_range('bf16', sg['e0'], sg['elems'])
        round_id = ((unit-u0)//bankmap.IL, block)
        if round_id != last_round:
            chain = 0; last_round = round_id
        # Fixed producer/consumer schedule. This is an offline max over source
        # identities and LAT8 recurrence, never a runtime ready predicate.
        edge = max(next_edge, arrivals[unit, block]+issue_offset,
                   last_chain.get(chain, -8)+8)
        last_chain[chain] = edge; next_edge = edge+1
        segment = runs[slot][0] if len(runs) == len(segments) else runs[0][0]
        address = runs[0][5]+index  # PP order is native element_order.
        operand = (1 << 14) | (block << 8) | unit
        word = (chain << 34) | (half << 33) | (segment << 30) | (operand << 15) | (address << 1) | 1
        if chain >= 16 or segment >= 8 or address >= 8192:
            raise ValueError('native programme aperture exceeded')
        records.append(dict(front_pin_edge=edge, core_issue_edge=edge+1,
            public_i1_edge=edge+2, public_i2x_edge=edge+3, word=word,
            chain=chain, half=half, segment=segment, unit=unit, block=block,
            position=0, logical_address=address, stream_pin_edge=arrivals[unit, block]))
        chain += 1
    if len(order) != sum(r[3]*r[6] for r in runs):
        raise ValueError('source word coverage')
    if {x['logical_address'] for x in records} != set(range(runs[0][5], runs[0][5]+len(order))):
        raise ValueError('source address coverage')
    # Actual selected BF front has PINREG1, FAST input1, match1: writes
    # FIFO at pin+3; core consumes programme at pin+1. Model old-state
    # availability and simultaneous push/pop before any hardware build.
    occupancy = 0; peak = 0
    pushes = {}
    for unit, block in arrivals:
        edge = arrivals[unit, block]+3
        pushes[edge] = pushes.get(edge, 0)+1
    pops = {r['core_issue_edge']:1 for r in records}
    for edge in range(max(max(pushes),max(pops))+1):
        if pops.get(edge,0) and occupancy == 0:
            raise ValueError('fixed programme FIFO underflow at core edge '+str(edge))
        occupancy += pushes.get(edge,0)-pops.get(edge,0)
        peak = max(peak,occupancy)
        if occupancy > 8:
            raise ValueError('fixed programme XF8 overflow at core edge '+str(edge))
    if occupancy:
        raise ValueError('source operand remains unconsumed')
    output.mkdir(parents=True, exist_ok=False)
    (output/'matrix.json').write_text(json.dumps(matrix, indent=2)+'\n')
    (output/'cfg.hex').write_text(''.join(f'{w:012x}\n' for w in cfg))
    (output/'phrom.hex').write_text(''.join(f'{w:018x}\n' for w in phrom))
    (output/'stream.hex').write_text(''.join(f'{w:012x}\n' for w in stream))
    programme = [0]*(records[-1]['front_pin_edge']+1)
    for record in records:
        programme[record['front_pin_edge']] = record['word']
    (output/'programme.hex').write_text(''.join(f'{w:010x}\n' for w in programme))
    (output/'issues.json').write_text(json.dumps(records, indent=2)+'\n')
    # Exact physical macro coordinates, including real base80 and all K4096.
    coordinates = [dict(logical_address=r['logical_address'],
        macro=4*pair+2*row+r['logical_address']%2,
        physical_row=r['logical_address']//2, output_row=2*segments[0]['row']+row,
        source_columns=[128*r['unit']+8*lane+r['block'] for lane in range(16)])
        for r in records for row in range(2)]
    (output/'weight_coordinates.json').write_text(json.dumps(coordinates, indent=2)+'\n')
    receipt = dict(schema='s81.canonical_bf_source_program.v1', stage=matrix['stage'],
        rank=0, phase=phase, pair=pair, K=matrix['K'], rows=matrix['rows'],
        issue_count=len(records), stream_edges=len(stream), programme_edges=len(programme),
        issue_offset=issue_offset, fp32_output=fp32_output,
        cfg_words=25, full_pair_words=sum(r[3]*r[6] for r in runs),
        canonical_pins=pins, stream_emitter_sha256=emitter_sha,
        source_pins={str(p.relative_to(TOOLS)):sha(p) for p in
          [Path(compiler.__file__), Path(bankmap.__file__), Path(controls.__file__)]},
        weight_payload='OPEN: exact released checkpoint matrix_word provider required',
        input_payload='OPEN: actual source producer operand snapshot required',
        ingress_contract='Declared front-pin offset; hardware gate must validate FIFO age and fault-only checks',
        numerical_gate=False, physical_gate=False,
        price=dict(macs_per_issue=32, weight_bits_per_issue=548,
                   operand_bits_per_stream_beat=1024, programme_bits_per_edge=38,
                   ingress_offset_edges=issue_offset, fifo_push_after_xb_pin=3, fifo_depth=8,
                   fifo_peak=peak, fifo_terminal=occupancy, core_issue_after_front_pin=1,
                   public_i1_after_front_pin=2, public_i2x_after_front_pin=3,
                   unchanged_arithmetic_pipeline=True),
        files={p.name:sha(p) for p in sorted(output.iterdir())})
    (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--canonical', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--issue-offset', type=int, required=True)
    parser.add_argument('--fp32-output', type=int, choices=(0, 1), required=True)
    args = parser.parse_args()
    if args.issue_offset < 1:
        parser.error('positive declared fixed ingress offset required')
    print(json.dumps(generate(args.canonical, args.output,
          issue_offset=args.issue_offset, fp32_output=bool(args.fp32_output)), indent=2))
