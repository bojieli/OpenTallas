#!/usr/bin/env python3
"""DISABLED one-phase BF row-label experiment; leaves production remapper alone."""
import argparse
import json
import os
from pathlib import Path
import sys


def emit(vector, field, phase, out, wrong_first_tag=False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import field_rank_images as F
    vector, field, out = map(Path, (vector, field, out))
    record = json.loads(field.read_text())
    meta = json.loads((vector / 'meta.json').read_text())
    ph = record['phases'][phase]
    assert record['frame'] == meta['die_frame']
    assert ph['phase'] == meta['field_phase'] == phase
    assert ph['fmt'] == 'bf16' and ph['rows'] == meta['nrows']
    assert ph['op'] == 'attn.wo_a', 'only the actual WOA rank-zero source experiment is admitted'
    tags = ph['row_index']
    assert tags == [t[1] for t in ph['tie']]
    assert len(set(tags)) == len(tags) and all(type(t) is int and 0 <= t < 16384 for t in tags)
    assert tags != list(range(len(tags))), 'use an actual nonzero ownership phase'
    out.mkdir(parents=True, exist_ok=False)
    for path in vector.iterdir():
        if path.is_file():
            os.link(path, out / path.name)
    changes = []
    for prefix in (meta['die_frame'], 'f'):
        for pair in meta['bf']['pairs']:
            for bank in range(7):
                name = f'{prefix}_c{pair}_{bank}.viamap.hex'
                path = out / name
                data = [int(v, 16) for v in path.read_text().split()]
                original = list(data)
                for index in F.ROW_WORDS:
                    if index % 7 != bank:
                        continue
                    address = 4 * phase + index // 7
                    value = F.word(data, address)
                    if value == 0 or value & 0x8000:
                        continue
                    local = value & 0xffff
                    assert local < len(tags), 'existing local BF row outside actual phase'
                    tag = local if wrong_first_tag and local == 0 else tags[local]
                    F.set_tag(data, address, tag)
                    assert F.word(data, address) == (value & ~0xffff) | tag
                    if tag != local:
                        changes.append(dict(image=name, address=address, local=local, candidate=tag))
                F.check_preserved_planes(original, data)
                if data != original:
                    path.unlink()
                    path.write_text(''.join(f'{v:0144x}\n' for v in data))
    args = (vector / 'ARGS').read_text().replace(str(vector), str(out))
    (out / 'ARGS').unlink()
    (out / 'ARGS').write_text(args)
    report = dict(status='DISABLED_BF_ROW_LABEL_EXPERIMENT', phase=phase, rows=tags,
                  changes=changes, wrong_first_tag=wrong_first_tag,
                  descriptors_preserved=True, production_enabled=False, added_cycles=0,
                  scope='BF-active/Q-idle source image label experiment; consuming mission contract unqualified')
    (out / 'row_overlay.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('vector', 'field', 'out'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--phase', type=int, required=True)
    p.add_argument('--wrong-first-tag', action='store_true')
    a = p.parse_args()
    r = emit(a.vector, a.field, a.phase, a.out, a.wrong_first_tag)
    print(r['status'], len(r['changes']), 'CFG row fields', flush=True)
