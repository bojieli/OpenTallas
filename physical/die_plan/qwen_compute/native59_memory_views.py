"""Physical views for the eight existing native59 writer banks (no RTL/cycle change)."""
from pathlib import Path
import json

MODULE = 'ot_sram_1r1w_32x512_m1'
PREFIX = 'u_bound.u_core.u_qb.u_qseat'
WIDTH, HEIGHT = 167.4, 76.14


def attach(raw):
    """Two mirrored columns put the 512-bit read outputs toward the mux spine.

    The outside write/control pins face the surrounding lane-local registers.
    Keep a 282.6-um central logic/clock corridor and 33.86-um row channels.
    These are physical views of memories already present in the native RTL.
    """
    t = raw['partition_types']['native59']
    w, h = t['outline_um']
    assert w >= 777.6 and h >= 518.4, (w, h)
    entries = []
    for i in range(8):
        col, row = i // 4, i % 4
        x, y, orient = (80.0 if col == 0 else 530.0), 40.0 + 110.0 * row, ('R0' if col == 0 else 'MY')
        entries.append(dict(inst=f'{PREFIX}.g_writer[{i}].u_mem', module=MODULE, status='reuse',
                            outline_um=[WIDTH, HEIGHT], origin_um=[x, y], orient=orient,
                            lef=f'physical/asap7_memory_macros/{MODULE}/{MODULE}.lef',
                            lib=f'physical/asap7_memory_macros/{MODULE}/{MODULE}_tt.lib',
                            note='Existing writer bank; outputs face central read mux, inputs face exterior; 0 added cycles'))
    names = {e['inst'] for e in entries}
    t['contents'] = [c for c in t['contents'] if c['inst'] not in names] + entries
    return entries


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); raw = json.loads(a.plan.read_text()); attach(raw)
    a.out.write_text(json.dumps(raw, separators=(',', ':'))+'\n')
