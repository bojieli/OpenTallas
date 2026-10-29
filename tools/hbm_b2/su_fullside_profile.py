#!/usr/bin/env python3
"""Select FULL/SIDE hardware explicitly without changing the VM address QID.

This emits a candidate only. Compiler role selection, source bind, arithmetic
qualification, model area and new physical masters remain required.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

SLICE = re.compile(r'^(  ot_hbm_su_static_pgslice_lg_s #\()([^\n]*)(\) (su_(NW|NE)([0-3])) \()', re.M)
EXPECTED = {f'su_{r}{g}' for r in ('NW', 'NE') for g in range(4)}
CAPABLE = {'su_NW0', 'su_NE0'}


def apply_profile(source, enabled):
    enabled = list(enabled)
    if len(enabled) != len(set(enabled)) or not set(enabled) <= CAPABLE:
        raise ValueError('FULL/SIDE enables must be unique retained G0 slice names')
    all_slices = re.findall(r'^  ot_hbm_su_static_pgslice_lg(?:_s)? #[^\n]* (su_(?:NW|NE|SW|SE)[0-3]) \(', source, re.M)
    if len(all_slices) != 8 or set(all_slices) != EXPECTED:
        raise ValueError('requires exactly the eight actual retained source slices')
    rows = []

    def patch(m):
        params = m[2]
        entries = re.findall(r'\.(\w+)\(([^()]*)\)', params)
        if len(entries) != len(dict(entries)):
            raise ValueError(m[4] + ': duplicate source parameter')
        old = dict(entries)
        if old.get('QID') != str({'NW': 2, 'NE': 3}[m[5]]) or old.get('G') != m[6]:
            raise ValueError(m[4] + ': VM role/group changed')
        if 'FULL_SIDE' in old:
            raise ValueError(m[4] + ': capability already selected; use original source')
        if m[4] in enabled:
            params += ', .FULL_SIDE(1)'
        rows.append(dict(instance=m[4],vm_qid=int(old['QID']),group=int(old['G']),
                         full_side=m[4] in enabled,added_data_cycles=0,
                         lane0_kind=2 if m[4] in enabled else 1 if m[6] in ('0','1') else 0))
        return m[1] + params + m[3]

    result = SLICE.sub(patch, source)
    if len(rows) != 8:
        raise ValueError('requires split-twin source; unsplit masters are unchanged')
    receipt = dict(schema='opentallas.hbm.fullside_candidate.v1',enabled=enabled,slices=rows,
                   source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                   candidate_sha256=hashlib.sha256(result.encode()).hexdigest(),
                   added_data_cycles=0,clock_pins_per_side=6,
                   status='CANDIDATE_NOT_ADOPTED',
                   obligations=['compiler operation target role','actual source bind',
                                'KIND2 and SIDE arithmetic token qualification',
                                'full/side source cuts and physical masters','model area/latency'])
    return result, receipt



def apply_actual_profile(source, enabled):
    """Materialize the selected split-parent alias before explicit capability.

    The current source manifest already substitutes all eight retained LG
    parents with LG_s. This makes that exact selection visible in a candidate
    source; it changes no underlying parent body or address QID.
    """
    original_hash = hashlib.sha256(source.encode()).hexdigest()
    source, count = re.subn(r'(?m)^(  )ot_hbm_su_static_pgslice_lg(?= #)',
                            r'\1ot_hbm_su_static_pgslice_lg_s', source)
    if count != 8:
        raise ValueError('requires exactly eight actual unsplit-parent caller spellings')
    result, receipt = apply_profile(source, enabled)
    receipt.update(original_actual_source_sha256=original_hash,
                   materialized_existing_split_parent_aliases=count)
    return result, receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('top',type=Path)
    p.add_argument('--enable',action='append',choices=sorted(CAPABLE),default=[])
    p.add_argument('--materialize-split-parent',action='store_true',
                   help='explicitly materialize the existing eight LG to LG_s manifest aliases')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists() or a.receipt.exists():
        p.error('use fresh output paths')
    selector=apply_actual_profile if a.materialize_split_parent else apply_profile
    result,receipt=selector(a.top.read_text(),a.enable)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.receipt.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(result);a.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
    print('FULL/SIDE candidate',a.enable,'added data cycles 0; fresh qualification required')


if __name__=='__main__':
    main()
