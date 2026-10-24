#!/usr/bin/env python3
"""Expand explicit bound FT chains to a reach ledger without touching leaf logic.

Input is a kit_rsync-converted bound module. Return to its logically equivalent
single-reset form so kit_rsync can regenerate local synchronizers for new taps.
Every added cycle is specified by ft_reach.resize's ledger; this is a G3 vehicle,
not a substitute for rebinding the complete die/compiler to the new latency table.
"""
import argparse
import json
import re
from pathlib import Path


def expand(text, changes):
    stages = set(re.findall(r'ot_dp_rsync_s([23])\s+u_rsync_t', text))
    if len(stages) > 1:
        raise ValueError('mixed reset synchronizer depths')
    ns = int(next(iter(stages))) if stages else 2
    text = re.sub(r'^\s*wire rst_n_t\d+;\s*\n', '', text, flags=re.M)
    text = re.sub(r'^\s*ot_dp_rsync_s\d+ u_rsync_t\d+ .*?\n', '', text, flags=re.M)
    text = re.sub(r'^\s*assign rst_n = rst_n_t0;\s*\n', '', text, flags=re.M)
    text = re.sub(r'\brst_n_t\d+\b', 'rst_n', text)
    if 'u_rst_sync' not in text:
        if '    wire rst_n;' not in text:
            raise ValueError('missing logical reset declaration')
        text = text.replace('    wire rst_n;', f'    wire rst_n;\n    ot_reset_sync #(.ASYNC_STAGES({ns})) u_rst_sync '
                            '(.clk(clk), .async_rst_n(arst_n), .sync_rst_n(rst_n));', 1)
    text = text.replace('ot_dp_ste #', 'ot_dp_st #')
    for c in changes:
        slot = c['slot']
        old, new = c['stations']
        if new <= old:
            raise ValueError('ledger must strictly increase station count')
        pat = rf'^(\s*)ot_dp_st #\(\.W\((\d+)\)\) u_ft_{slot}_o_{old-1} .*?;$'
        m = re.search(pat, text, re.M)
        if not m:
            raise ValueError('missing terminal stage ' + slot)
        ind, w = m.group(1), int(m.group(2))
        last = m.group(0)
        if f'.q({slot}_o[' not in last or f'.eq({slot}_o[' not in last:
            raise ValueError('terminal stage is not the output driver: ' + slot)
        wires = ''.join(f'{ind}wire [{w}:0] {slot}_o_s{j};\n' for j in range(old-1, new-1))
        last = last.replace(f'.q({slot}_o[', f'.q({slot}_o_s{old-1}[').replace(
                            f'.eq({slot}_o[', f'.eq({slot}_o_s{old-1}[')
        extra = []
        for j in range(old, new):
            inp = f'{slot}_o_s{j-1}'
            dst = f'{slot}_o_s{j}' if j < new-1 else f'{slot}_o'
            extra.append(f'{ind}ot_dp_st #(.W({w})) u_ft_{slot}_o_{j} (.clk(clk), .rst_n(rst_n), '
                         f'.d({inp}[{w-1}:0]), .ea({inp}[{w}]), .q({dst}[{w-1}:0]), .eq({dst}[{w}]));')
        text = text[:m.start()] + wires + last + '\n' + '\n'.join(extra) + text[m.end():]
    return text


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('rtl')
    ap.add_argument('ledger')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    Path(a.out).write_text(expand(Path(a.rtl).read_text(), json.loads(Path(a.ledger).read_text())))
