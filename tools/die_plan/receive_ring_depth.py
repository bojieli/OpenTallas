"""Emit opt-in pre-GPL receiving-ring regions from bound bit-role paths."""

import math
import re
from pathlib import Path

import logic_cluster


def _number(value):
    return type(value) in (float, int) and math.isfinite(value)


def _id(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', value)


def _box(rect):
    return (
        isinstance(rect, list) and len(rect) == 4 and all(_number(v) for v in rect)
        and rect[0] < rect[2] and rect[1] < rect[3]
    )


def _overlap(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def _contains(outer, inner):
    return (
        outer[0] <= inner[0] and outer[1] <= inner[1]
        and inner[2] <= outer[2] and inner[3] <= outer[3]
    )


def validate(t, tn, *, no_core_rows=()):
    value = t.get('receive_ring_depth')
    if value is None:
        return None
    bad = f'{tn}: receive_ring_depth'
    if not isinstance(value, dict) or set(value) != {'version', 'source_bins', 'regions'} or value['version'] != 1:
        raise ValueError(f'{bad} needs version 1, source_bins and regions')
    if any(not isinstance(value[k], list) or not value[k] for k in ('source_bins', 'regions')):
        raise ValueError(f'{bad} needs nonempty region and source budget lists')
    bands = t.get('clock', {}).get('landing_contract', {}).get('bands', {})
    w, h = t['outline_um']
    boxes = {}
    static_rects = [r['rect_um'] for r in logic_cluster.validate(t, tn)]
    for region in value['regions']:
        if not isinstance(region, dict) or set(region) != {'name', 'ring', 'rect_um', 'capacity_um2'}:
            raise ValueError(f'{bad} invalid receiving region')
        name, ring, rect, capacity = (region[k] for k in ('name', 'ring', 'rect_um', 'capacity_um2'))
        if not _id(name) or name in boxes or not _id(ring) or ring not in bands or bands[ring].get('hard_core'):
            raise ValueError(f'{bad} duplicate region or unknown soft ring {name!r}/{ring!r}')
        if not _box(rect) or not _contains([0, 0, w, h], rect) or not _contains(bands[ring]['rect_um'], rect):
            raise ValueError(f'{bad} {name}: region must lie inside its ring and type outline')
        if any(_overlap(rect, box) for box in [*boxes.values(), *static_rects, *(b for _, b in no_core_rows)]):
            raise ValueError(f'{bad} {name}: receiver overlaps another cluster or rowless PHY domain')
        gross = (rect[2] - rect[0]) * (rect[3] - rect[1])
        if not _number(capacity) or not 0 < capacity <= logic_cluster.MAX_UTIL * gross - 4.0 + .00001:
            raise ValueError(f'{bad} {name}: receiving capacity exceeds the physical reserve')
        boxes[name] = rect
    used_regions = set()
    used_bins = set()
    for source in value['source_bins']:
        if not isinstance(source, dict) or set(source) != {'key', 'required_um2', 'picks'}:
            raise ValueError(f'{bad} invalid source bin')
        key = source['key']
        if not isinstance(key, list) or len(key) != 2 or any(type(v) is not int or v < 0 for v in key):
            raise ValueError(f'{bad} invalid source bin coordinate {key!r}')
        coordinate = tuple(key)
        if coordinate in used_bins:
            raise ValueError(f'{bad} duplicate source bin {key}')
        used_bins.add(coordinate)
        need, picks = source['required_um2'], source['picks']
        if not _number(need) or need <= 0 or not isinstance(picks, list) or not picks:
            raise ValueError(f'{bad} {key}: a positive source budget and role paths are required')
        for pick in picks:
            if not isinstance(pick, dict) or set(pick) != {'region', 'anchor', 'path', 'area_um2'}:
                raise ValueError(f'{bad} {key}: invalid role pick')
            region, anchor, path, area = (pick[k] for k in ('region', 'anchor', 'path', 'area_um2'))
            if not _id(region) or region not in boxes:
                raise ValueError(f'{bad} {key}: unknown receiver {region!r}')
            used_regions.add(region)
            if (not isinstance(anchor, list) or len(anchor) != 3 or anchor[1] not in ('storage', 'read')
                    or any(type(anchor[i]) is not int or anchor[i] < 0 for i in (0, 2))):
                raise ValueError(f'{bad} {key}: invalid native chunk/index anchor')
            if (not isinstance(path, list) or not 1 <= len(path) <= 6 or any(
                not isinstance(hop, list) or len(hop) != 2 or not all(_id(v) for v in hop)
                for hop in path
            ) or path[0][0] != 'D'):
                raise ValueError(f'{bad} {key}: invalid named data-pin path')
            if not _number(area) or area <= 0:
                raise ValueError(f'{bad} {key}: invalid role area')
    if used_regions != boxes.keys():
        raise ValueError(f'{bad} every receiver must have at least one source role')
    return value


def config_lines(value):
    """Translate only schema-guarded scalar tokens into Tcl lists."""
    for region in value['regions']:
        name, ring, rect, cap = (region[k] for k in ('name', 'ring', 'rect_um', 'capacity_um2'))
        coords = ' '.join(f'{x:.5f}' for x in rect)
        yield f'dict set rx_regions {name} {{{ring} {{{coords}}} {cap:.5f}}}'
    for source in value['source_bins']:
        x, y = source['key']
        yield f'dict set rx_floor {{{x} {y}}} {source["required_um2"]:.5f}'
        for pick in source['picks']:
            chunk, role, index = pick['anchor']
            traversal = ' '.join('{' + ' '.join(hop) + '}' for hop in pick['path'])
            yield (
                f'lappend rx_picks {{{{{x} {y}}} {pick["region"]} '
                f'{{{chunk} {role} {index}}} {{{traversal}}} {pick["area_um2"]:.5f}}}'
            )


def tcl(P, tn, *, no_core_rows=()):
    value = validate(P.types[tn], tn, no_core_rows=no_core_rows)
    if value is None:
        return ''
    source = Path(__file__).with_suffix('.tcl').read_text()
    return '\n'.join([
        'uplevel #0 {',
        source,
        *logic_cluster.REGION_TCL,
        'set rx_regions {}; set rx_floor {}; set rx_picks {}',
        *config_lines(value),
        'ot_rx_depth_place $rx_regions $rx_floor $rx_picks',
        'unset rx_regions rx_floor rx_picks',
        '}',
        '',
    ])
