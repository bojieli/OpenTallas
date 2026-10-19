#!/usr/bin/env python3
"""Recover real-operand Q writes from existing native 12-slice logs, never an admission certificate."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def recover(root, layer):
    root = Path(root)
    run = root / 'runs' / f'L{layer}_qk'
    log, events, lower = [run / n for n in ('run_qk_m0.log', 'run_qk_m0.ev', 'lowering_qk.json')]
    fixture = root / 'fx' / f'L{layer}_qk.npz'
    outcome = (run / 'bench.out').read_text().splitlines()[0]
    if 'qk PASS' not in outcome or 'isa_gold_words=768/768' not in outcome:
        raise ValueError('source run lacks real golden PASS')
    trace, words = {}, []
    for line in log.read_text().splitlines():
        parts = line.split()
        if len(parts) != 3 or parts[1] != 'S0DD':
            continue
        c, w = int(parts[0]), int(parts[2], 16)
        if not w >> 547 & 1 or (w >> 545) & 3:
            continue
        mask = (w >> 537) & 255
        words.append(dict(edge_w5=c, word=f'{w:0137x}'))
        for lane in range(8):
            if not mask >> lane & 1:
                continue
            addr = (w >> (345 + 24*lane)) & 0xffffff
            data = (w >> (89 + 32*lane)) & 0xffffffff
            if addr not in range(512) or addr in trace:
                raise ValueError(f'invalid/duplicate Q seat {addr}')
            trace[addr] = dict(seat=addr, beat=addr//16, edge_w5=c, bits=f'{data:08x}')
    if set(trace) != set(range(512)):
        raise ValueError('incomplete Q seat coverage')
    with np.load(fixture) as fx:
        golden = fx['gold_q'].astype(np.float32).view(np.uint32).reshape(-1)
    if len(golden) != 512 or any(int(trace[i]['bits'], 16) != int(golden[i]) for i in range(512)):
        raise ValueError('Q trace differs from real ISA golden')
    expected = json.loads(lower.read_text())['expected']['d2d']
    # Compare all96 Q/K/V pin edges to the compiler schedule using ONE shared origin.
    all_edges = [int(s.split()[0]) for s in log.read_text().splitlines() if ' S0DD ' in s]
    relative = sorted(int(x['edge_w5']) for x in expected)
    origin = min(all_edges) - min(relative)
    if sorted(all_edges) != [origin+x for x in relative]:
        raise ValueError('observed pin edges disagree with compiler programme')
    return dict(schema='opentallas.qwen.q_producer_boundary_recovery.v1',
                production_bound=False, advance_admitted=False, layer=layer, position=8191,
                source_commit='2cdba303d', vehicle='tb_qfd_dv2 N12 existing Verilator5.050 executable',
                boundary='dvs_W5.dd_wo', origin_in_local_bench=origin, seat_count=512,
                input_digests={k:sha(v) for k,v in dict(log=log, events=events, lowering=lower, fixture=fixture).items()},
                actual_source_slice_sha256=sha(root/'src/rtl/qwen_dv/qfd_dv_slice2.sv'),
                source_outcome=outcome, words=words, seats=[trace[i] for i in range(512)],
                last_q_write_w5=[max(trace[16*b+j]['edge_w5'] for j in range(16)) for b in range(32)],
                restrictions=['QKV and r VM inputs are bench-landed real operands; tile/QKV producer is not connected',
                              'event source is direct compiled slice commands/table writes, not deployable controller PW/DW',
                              'source predates dv2f18dh2; no substitute for its production programme or SAFE2 successor GEN',
                              'local bench origin has no proven relation to production layer start; no QSLOT events generated'])


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    for layer in (0,1):
        r=recover(a.root,layer)
        (out/f'L{layer}_q_trace.json').write_text(json.dumps(r,indent=1)+'\n')
        print(f'Q_BOUNDARY_RECOVERY L{layer} PASS 512 unique seats bit-exact; 96 compiler-pin edges; production_bound=false')
