#!/usr/bin/env python3
"""Restore the SU bank16/row7 installation ABI without changing frozen ports.

The sparse collar accepts ordered banks, contiguous rows starting at zero in
 each bank, source-defined legal bank apertures, and an exact per-generation
write count in E01. Old dense views cannot implement this parameter variant.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def apply(contract, repo):
    inst = contract['instances']
    collar = inst['col_su']
    assert collar['master'] == 'ot_hbm_static_cfg_collar'
    assert all(collar['params'][k] == v for k, v in dict(PAGE_W=12, NS=1, XSER=1).items())
    sources = {}
    caps = None
    for q in ('SW', 'SE', 'NW', 'NE'):
        producer = inst['pgp_' + q]
        assert producer['master'] == 'ot_hbm_su_programme_pslice_c5'
        assert producer['params']['SB'] == 2470
        source = Path(producer['source'])
        if not source.is_absolute():
            source = Path(repo) / source
        data = source.read_bytes()
        text = data.decode()
        if 'DICT_CAP' in producer['params']:
            selected = producer['params']['DICT_CAP']
        else:
            m = re.search(r'parameter\s+\[32\*NC-1:0\]\s+DICT_CAP\s*=\s*(\{[^}]+\})', text)
            assert m, 'selected programme producer has no explicit dictionary aperture'
            selected = m.group(1)
        assert caps is None or caps == selected, 'different programme apertures need separate collars'
        caps = selected
        sources[q] = dict(path=str(source), sha256=hashlib.sha256(data).hexdigest())
    collar['params'].update(SPARSE_SU=1, SU_DICT_CAP=caps)
    collar['physical_view'] = 'physical/ref_tile/hdie_col_su_sparse_1022/views/ot_hbm_static_cfg_collar'
    # A missing requested view causes a truthful SYNTH wrapper; the old dense
    # hdie_col_su_r1 view must not silently satisfy this port-identical variant.
    collar['note'] += ' | Sparse SU installation: legal bank aperture; per-bank ordered rows; E01 exact write count; fresh generation clears need/operand ownership.'
    return dict(schema='opentallas.hbm.su-sparse-install.v1', producer_sources=sources,
                params=collar['params'], requested_physical_view=collar['physical_view'],
                added_data_edges=0, added_control_bits=24,
                qualification='functional source restoration; physical closure still required')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input'); ap.add_argument('output'); ap.add_argument('--repo', required=True)
    ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = json.loads(Path(a.input).read_text())
    r = apply(c, a.repo)
    Path(a.output).write_text(json.dumps(c, indent=1) + '\n')
    Path(a.report).write_text(json.dumps(r, indent=1) + '\n')
    print('SU_SPARSE_INSTALL_SOURCE_PASS col_su SPARSE_SU=1 exact producer apertures; SYNTH until matching view exists')


if __name__ == '__main__':
    main()
