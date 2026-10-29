#!/usr/bin/env python3
"""Export actual DMA<->VM-bank edge bits from a current flattened native source.

Directions, widths, clock/reset nets and every connected bit come from the
elaborated cells. This does not infer directions from plan station declarations.
Usage: dma_native_edges.py FLAT.pkl TOP.sv OUT.json [--quarter NW|NE]
"""
import argparse
import json
import pickle
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'die_plan'))
from b2_top import Die

def export(flat, top, quarter):
    cells = {c.path: c for c in flat.cells}
    die = Die(top, [])
    root = 'hb_dbk_' + quarter
    dma = cells[root]
    req_width, ret_width = len(dma.ports['rq']), len(dma.ports['rr'])
    if req_width != 8 * 17 or ret_width != 8 * 257:
        raise ValueError(f'unsupported actual DMA shape rq={req_width}, rr={ret_width}')
    rows = []
    for bank in range(8):
        bank_name = f'vmb_{quarter}{bank}'
        for sn, sp, dn, dp, sb, db in (
            (root, 'rq', bank_name, 'rq1', list(range(bank * 17, bank * 17 + 17)), list(range(17))),
            (bank_name, 'rr1', root, 'rr', list(range(257)), list(range(bank * 257, bank * 257 + 257))),
        ):
            source, sink = cells[sn], cells[dn]
            if source.dirs[sp] != 'output' or sink.dirs[dp] != 'input':
                raise ValueError(f'wrong actual direction {sn}.{sp}->{dn}.{dp}')
            if any(source.ports[sp][a] != sink.ports[dp][b] for a, b in zip(sb, db)):
                raise ValueError(f'edge is not actually direct: {sn}.{sp}->{dn}.{dp}')
            row = dict(bank=bank, src=sn, src_module=source.module, src_port=sp, src_bits=sb,
                       dst=dn, dst_module=sink.module, dst_port=dp, dst_bits=db, width=len(sb),
                       source_nets=[source.ports[sp][a] for a in sb], actual_source_stages=0,
                       valid_src_bit=sb[-1], valid_dst_bit=db[-1])
            for label, cell, name in (('source', source, sn), ('sink', sink, dn)):
                for kind, port in (('clock', 'clk'), ('reset', 'rst_n')):
                    row[f'{label}_{kind}_nets'] = cell.ports[port]
                    row[f'{label}_{kind}_expr'] = die.insts[name]['conns'][port]
            rows.append(row)
    return dict(schema='hbm.actual_dma_bank_edges.v1', quarter=quarter, actual_native_source=str(top),
                dbk_rq_width=req_width, dbk_rr_width=ret_width, dbk_parameters=dma.params,
                groups=rows, terminal_equality=True,
                note='Source/sink directions and every connected bit come from current native elaboration. '
                     'Clock/reset expressions identify the caller supplies. High-bit valid positions follow '
                     'the request17/response257 contract; this export does not qualify transport timing or reset delivery.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('flat', type=Path)
    parser.add_argument('top', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--quarter', choices=('NW', 'NE'), default='NW')
    args = parser.parse_args()
    with args.flat.open('rb') as handle:
        flat = pickle.load(handle)
    result = export(flat, args.top, args.quarter)
    result['flat'] = str(args.flat)
    args.out.write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(dict(groups=len(result['groups']), rq=result['dbk_rq_width'], rr=result['dbk_rr_width'])))

if __name__ == '__main__':
    main()
