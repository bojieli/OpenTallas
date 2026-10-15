#!/usr/bin/env python3
"""Derive actual NORM-tree row reservations from the source-pinned v22 serial layout.

Candidate geometry only. Whole slab/clock/RTL qualification and croot anchors are
not established by this row substitution.
"""
import copy
import hashlib
import json
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PIN_REF = '7a483898c1737dbd1216c23aef56f8cdfb970f0a'

def derive():
    path = ROOT / 'results/arch/hier_contract_1011/s81_v22_hc_ret.json'
    raw = path.read_bytes()
    old = json.loads(raw)['sub_layouts']['ot_s81_hc_cth']
    rows = []
    shift = 0.0
    for original in old['rows']:
        row = copy.deepcopy(original)
        row['y'] = round(row['y'] + shift, 3)
        if row['tile'] == 'ctfx':
            row.update(tile='ctfxs_nt', cell='ot_s81_hc_ctfxs_nt', h=25.92)
            rows.append(row)
            rows.append(dict(tile='ctfl_nt', cell='ot_s81_hc_ctfl_nt', w=576.72, h=25.92,
                             y=round(row['y'] + 25.92, 3)))
            shift += 25.92 - original['h'] + 25.92
        else:
            if row['tile'] == 'ctfs':
                row.update(tile='ctfs_nt', cell='ot_s81_hc_ctfs_nt')
            rows.append(row)
    height = round(old['outline']['h'] + shift, 3)
    assert height == 810.0 and shift == 38.88
    by = {r['tile']: r for r in rows}
    assert all(a['y'] + a['h'] <= b['y'] + 1e-6 for a, b in zip(rows, rows[1:]))
    def pins(master):
        p = 'physical/s81_die_pins/v24_hc_norm_spread_candidate/' + master + '.json'
        return json.loads(subprocess.check_output(['git', 'show', PIN_REF + ':' + p]))
    ps = {k: pins('ot_s81_hc_' + k) for k in ('ctfs_nt', 'ctfn', 'ctfxs_nt')}
    def xy(short, port, previous=False):
        row = by[short]
        rec = ps[short]
        result = []
        for face, layer, along, direction in rec['ports'][port]['per_bit']:
            assert face in ('N', 'S'), (short, port, face)
            x = along if face in 'NS' else (0 if face == 'W' else row['w'])
            y = -row['y'] - (0 if face == 'N' else row['h'])
            if previous:
                y += height
            result.append((x, y))
        return result
    def seam(src, dst):
        a, b = xy(*src), xy(*dst)
        assert len(a) == len(b)
        d = [abs(p[0]-q[0]) + abs(p[1]-q[1]) for p, q in zip(a, b)]
        return dict(bits=len(d), max_manhattan_um=round(max(d), 3), over500=sum(x>500 for x in d))
    seams = {}
    for signal, receiver, dest in [('fd_out','ctfn','fd_in'), ('fd_out','ctfxs_nt','fd_in'),
                                    ('fv_out','ctfn','fv_in'), ('fv_out','ctfxs_nt','fv_in')]:
        a = xy('ctfs_nt', signal, True)
        b = xy(receiver, dest)
        a = a[:len(b)]
        assert len(a) == len(b)
        ds = [abs(p[0]-q[0]) + abs(p[1]-q[1]) for p,q in zip(a,b)]
        seams[signal + '_to_' + receiver] = dict(bits=len(ds), max_manhattan_um=round(max(ds),3), over500=sum(x>500 for x in ds))
    seams['fdm_ctfn_to_ctfs_nt'] = seam(('ctfn','fdm'), ('ctfs_nt','fdm'))
    return dict(schema='opentallas.s81.nt_rows.candidate.v1', native_qualified=False,
                source_serial_contract=str(path.relative_to(ROOT)), source_sha256=hashlib.sha256(raw).hexdigest(),
                pin_source_commit=PIN_REF, outline_um=[576.72, height], rows=rows, spare_um=old['spare_um'],
                growth_per_row_um=shift, supersedes_incorrect_790_56_budget=True, seams=seams,
                parent_maximum_row_counts=dict(head=10,tail=12),
                legacy_hc_corridor_um=round(1226.88-(10+12)*shift,3),
                open=['CTfl to all eight CLOSED CTPL current810 origins requires139bit repin; oldv24 has139/9080 over500 max512.694',
                      'First crootr and last chain anchor pins', 'Actual 64 row/source chain fold and controls',
                      'Native reset/clock delivery/TT setup/FF hold/DRC0/static calendar'])

if __name__ == '__main__':
    import sys
    out = Path(sys.argv[1])
    out.write_text(json.dumps(derive(), indent=2) + '\n')
