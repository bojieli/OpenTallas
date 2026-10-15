#!/usr/bin/env python3
"""Make temporary pin-identical PDN masters; route masters are never edited.

Only plain rectangular OBS are supported. Unsupported geometry fails closed.
Bounding a layer's rectangles can only add obstruction, never expose metal.
"""
import argparse
from decimal import Decimal
from pathlib import Path
import re

PREFIX = 'OT_PDN_BBOX_'


def compact_obs(body):
    match = re.search(r'(?m)^\s*OBS\s*\n(.*?)^\s*END\s*$', body, re.S)
    if not match:
        return body
    text = match[1]
    layers = []
    for statement in text.split(';'):
        words = statement.split()
        if not words:
            continue
        if words[0] == 'LAYER' and len(words) == 2:
            layers.append((words[1], []))
        elif words[0] == 'RECT' and len(words) == 5 and layers:
            box = tuple(Decimal(x) for x in words[1:])
            if box[0] >= box[2] or box[1] >= box[3]:
                raise ValueError('invalid obstruction rectangle')
            layers[-1][1].append(box)
        else:
            raise ValueError('unsupported OBS statement: ' + statement.strip())
    by_layer = {}
    for layer, boxes in layers:
        if not boxes:
            raise ValueError('empty obstruction layer')
        by_layer.setdefault(layer, []).extend(boxes)
    result = ['  OBS']
    for layer, boxes in by_layer.items():
        bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))
        assert all(bbox[0] <= b[0] and bbox[1] <= b[1] and
                   bbox[2] >= b[2] and bbox[3] >= b[3] for b in boxes)
        result += [f'    LAYER {layer} ;', '      RECT ' + ' '.join(map(str, bbox)) + ' ;']
    result.append('  END')
    return body[:match.start()] + '\n'.join(result) + '\n' + body[match.end():]


def aliases(text, names):
    outputs = []
    seen = set()
    # LEF master names are single tokens; PIN/PORT END lines do not carry the master name.
    pattern = re.compile(r'(?m)^MACRO (\S+)\s*\n')
    for match in pattern.finditer(text):
        name = match[1]
        if name not in names:
            continue
        if name.startswith(PREFIX):
            raise ValueError('recursive PDN master')
        end = re.search(r'(?m)^END ' + re.escape(name) + r'\s*$', text[match.end():])
        if not end or name in seen:
            raise ValueError('missing or duplicate master: ' + name)
        body = text[match.end():match.end() + end.start()]
        outputs.append(f'MACRO {PREFIX}{name}\n' + compact_obs(body) + f'END {PREFIX}{name}\n')
        seen.add(name)
    if seen != names:
        raise ValueError('missing masters: ' + repr(sorted(names - seen)))
    return 'VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(outputs) + 'END LIBRARY\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('names')
    parser.add_argument('output')
    args = parser.parse_args()
    source = Path(args.source)
    # OpenROAD emits one LEF per library, suffixed _1, _2, ... .
    paths = [source] + sorted(source.parent.glob(source.stem + '_*.lef'))
    text = '\n'.join(path.read_text() for path in paths)
    Path(args.output).write_text(aliases(text, set(Path(args.names).read_text().splitlines())))
