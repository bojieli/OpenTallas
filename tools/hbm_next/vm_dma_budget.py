#!/usr/bin/env python3
"""Inventory actual finite-VM boundary DMA and a hypothetical generic mover service floor.

This is a HYPOTHETICAL GENERIC-MOVER bandwidth bound, not a selected-native
service bound, measured RTL timing, or a token-rate model. The current native
top directly instantiates static DMA BACK engines, which have wider bank ports.
LOAD dispatch/source selection is still unproven; this model cannot price it.
The native mover publishes at most one 256-bit destination sector per cycle;
its optional raw KVW STORE consumes at most 512 bits per cycle. HBM die aggregate
bandwidth cannot replace these narrower source interfaces. Full-wait commands
serialize source consumption; STORE posted completion does not mean zero bytes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys


def transfer(r, kind):
    if kind not in ('load', 'store', 'epoch_store'):
        return None
    if r.unit != 'DMA' or r.op != ('LOAD' if kind == 'load' else 'STORE'):
        raise ValueError('boundary metadata does not match native DMA operation')
    if r.param != 0 or r.wait != 65535:
        raise ValueError('only current linear full-wait boundary commands are bounded')
    a, o = r.desc['A'], r.desc['O']
    if (a.fmt not in ('U32', 'FP32') or o.fmt != a.fmt or
            a.m != 1 or o.m != 1 or a.n != o.n or a.n <= 0 or
            any(d.ibcast or d.istride not in (0, 1) or d.indexed or
                d.n_sel not in (0, 63) or d.dyn_mul or d.lstride or d.l1stride
                for d in (a, o))):
        raise ValueError('boundary shape requires another source service model')
    src, dst = ('HBM', 'VM') if r.op == 'LOAD' else ('VM', 'HBM')
    if a.space != src or o.space != dst:
        raise ValueError('boundary DMA direction differs')
    h, vm = (a, o) if r.op == 'LOAD' else (o, a)
    if h.base >> 37 or h.base % 32 or vm.base % 8 or a.n % 8:
        raise ValueError('boundary needs aligned whole-sector linear addressing')
    nbytes = 4 * a.n
    width = 32 if r.op == 'LOAD' else 64
    return dict(op=r.op, bytes=nbytes, stack=(h.base >> 35) & 3,
                stack_local_begin=h.base & ((1 << 35)-1),
                stack_local_end=(h.base & ((1 << 35)-1)) + nbytes,
                mode=h.base >> 37, max_source_bytes_per_cycle=width,
                optimistic_source_cycles=(nbytes + width - 1) // width)


def budget(chain_path, decode, stack_bytes=22_500_000_000):
    chain_path = Path(chain_path)
    chain = json.loads(chain_path.read_text())
    rows = []
    for ph in chain['phases']:
        blob = (chain_path.parent/ph['fragment']).read_bytes()
        for meta in ph['records']:
            r, _, _ = decode(blob, meta['offset'])
            row = transfer(r, meta['kind'])
            if row is not None:
                rows.append(dict(stage=ph.get('stage', 0), slot0=ph['slot0'],
                                 offset=meta['offset'], kind=meta['kind'], **row))
    invalid = [x for x in rows if x['stack_local_end'] > stack_bytes]
    by_op = {op: dict(records=sum(x['op'] == op for x in rows),
                     bytes=sum(x['bytes'] for x in rows if x['op'] == op),
                     source_cycles=sum(x['optimistic_source_cycles'] for x in rows if x['op'] == op))
             for op in ('LOAD', 'STORE')}
    return dict(schema='opentallas.hbm.vm_boundary_dma_budget.v2',
                status='HYPOTHETICAL_GENERIC_MOVER_ONLY_NOT_CURRENT_NATIVE_COST',
                source_range=chain['source_range'], by_op=by_op,
                scratch_reserved=chain.get('scratch_reserved', False),
                total_boundary_bytes=sum(x['bytes'] for x in rows),
                hypothetical_generic_mover_source_cycles=sum(x['optimistic_source_cycles'] for x in rows),
                hbm_stack_records=dict(sorted(Counter(str(x['stack']) for x in rows).items())),
                all_commands_linear_full_wait=True, rows=rows,
                current_native_cost_model_qualified=False,
                current_native_dispatch_status='BLOCKED: observed static BACK engines use stack2; scratch uses stack3; LOAD and VM ownership unproven',
                current_native_observed_back=dict(master='ot_hgi_dma_back_static_vp4_banks_cp', instances=['hb_dbk_NE','hb_dbk_NW'], stk=2, rr_rt=80, max_port_bytes_per_cycle=256),
                physical_capacity=dict(status='FAIL' if invalid else 'PASS',
                                       stack_bytes=stack_bytes, invalid_records=len(invalid),
                                       maximum_local_end=max(x['stack_local_end'] for x in rows),
                                       source='ot_hgi_dma_{front,back,engines}.sv STACK_BYTES default22_500_000_000'),
                assumptions=['HYPOTHETICAL selection of generic mover LOAD32B/cycle and KVW STORE64B/cycle; NOT current static BACK',
                             'one issuing GENERIC mover in the hypothesis; actual native dispatch not established',
                             'full waits serialize source consumption; posted write acknowledgement may lag'],
                excluded=['HBM request/refresh/response and VM service latency',
                          'command decode, all-unit drains and body arithmetic',
                          'original programme traffic already priced elsewhere',
                          'full-programme region repetition, scratch reservation and B2 QID dispatch authority'],
                whole_programme_qualified=False, measured_token_rate=None)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--chain', required=True)
    ap.add_argument('--compiler-tools', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--stack-bytes', type=int, default=22_500_000_000)
    a = ap.parse_args()
    root = Path(a.compiler_tools)
    sys.path[:0] = [str(root/'hbm_next'), str(root)]
    import isa_rows
    result = budget(a.chain, isa_rows.decode_one, a.stack_bytes)
    Path(a.out).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
