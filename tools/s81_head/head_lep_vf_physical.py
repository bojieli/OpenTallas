#!/usr/bin/env python3
"""Apply the measured LEP vF placement to its existing hard-core inventory.

No RTL, cycle, tap or view changes: move the 45 already-declared SRAM leaves
and publish the matching native register-stage rectangles. Pair sites remain
fixed. The profile is an extracted physical result, not a new macro hierarchy.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

TYPE = 'hd_lep0N'
CONTENT = 'u_core'
MODULE = 'ot_s81hd_lep0N_noidx_core'
PAIR_MODULE = 'ot_s81hd_lep_pair'
VF_PARAMS = {'CH_B': "4'b1111", 'PAIR': 1, 'KTX': "16'h0000",
             'KRX': "16'h1220", 'TXI': "16'h1221", 'PIN': 2,
             'POUT': 3, 'PLW': 3, 'COL0': 2}
PROFILE = Path(__file__).with_name('profiles') / 'head_lep_vf_placement.json'


def load_profile(path=PROFILE):
    return json.loads(Path(path).read_text())


def apply(raw, profile):
    """Return a deep copy with only measured SRAM sites and stage groups changed.

    Fail on a different vF parameter tuple, macro inventory, pair placement,
    conflicting stage contract, or an attempted duplicate physical-parts form.
    The caller owns plan-event and schema validation in its current source tree.
    """
    if profile.get('schema') != 'opentallas.head_lep_vf_physical.v1':
        raise ValueError('expected LEP vF physical profile schema v1')
    parts = profile.get('physical_parts', [])
    pairs = profile.get('pair_sites', [])
    groups = profile.get('native_stage_groups', [])
    if len(parts) != 45 or len(pairs) != 4 or len(groups) != 24:
        raise ValueError('profile must contain 45 SRAM sites, four pairs, 24 stage rows')
    if len({g['tag'] for g in groups}) != 19:
        raise ValueError('profile must describe exactly 19 native stage tags')
    part_by_name = {p['physical_inst']: p for p in parts}
    pair_by_name = {p['inst']: p for p in pairs}
    if len(part_by_name) != 45 or len(pair_by_name) != 4 or set(part_by_name) & set(pair_by_name):
        raise ValueError('profile macro instance names must be unique and disjoint')
    if not all(p['physical_master'].startswith('ot_sram_') for p in parts):
        raise ValueError('all 45 profile parts must be existing SRAM leaves')
    if any(not g.get('prefix') or len(g.get('rect_um', [])) != 4 or
           g['rect_um'][0] >= g['rect_um'][2] or g['rect_um'][1] >= g['rect_um'][3]
           for g in groups):
        raise ValueError('native stage groups require a prefix and positive rectangle')

    out = copy.deepcopy(raw)
    if out.get('die', {}).get('name') != 's81_head':
        raise ValueError('HEAD plan required')
    t = out['partition_types'][TYPE]
    contents = [c for c in t.get('contents', []) if c.get('inst') == CONTENT]
    if len(contents) != 1 or contents[0].get('module') != MODULE:
        raise ValueError('expected exactly one native LEP u_core content')
    content = contents[0]
    if content.get('params') != VF_PARAMS:
        raise ValueError('full exact nine-parameter LEP vF tuple required')
    if content.get('physical_parts'):
        raise ValueError('SRAMs are already hard_cores; physical_parts would duplicate them')
    cores = t.get('hard_cores', [])
    core_by_name = {c['inst']: c for c in cores}
    expected = {n: p['physical_master'] for n, p in part_by_name.items()}
    expected.update({n: PAIR_MODULE for n in pair_by_name})
    if len(cores) != 49 or len(core_by_name) != 49 or set(core_by_name) != set(expected):
        raise ValueError('expected exactly the existing four pairs plus 45 SRAM hard cores')
    for name, master in expected.items():
        if core_by_name[name].get('module') != master:
            raise ValueError(f'hard-core master changed for {name}: expected {master}')
    for name, site in pair_by_name.items():
        c = core_by_name[name]
        if c.get('origin_um') != site['origin_um'] or c.get('orient', 'R0') != site['orient']:
            raise ValueError(f'pair site/orientation changed: {name}')
        if c.get('track_offset_um', [0.0, 0.0]) != [0.0, 0.0]:
            raise ValueError(f'pair track offset changed: {name}')
    for name, site in part_by_name.items():
        c = core_by_name[name]
        offset = c.get('track_offset_um', [0.0, 0.0])
        # type_macros adds track_offset_um; keep that existing metadata while
        # making the effective placed origin equal the extracted DB position.
        c['origin_um'] = [round(site['origin_um'][k] - offset[k], 6) for k in (0, 1)]
        c['orient'] = site['orient']

    landing = t['clock'].setdefault('landing_contract', {})
    contract = {'schema': 'opentallas.native_stage_groups.v1', 'content': CONTENT,
                'module': MODULE, 'params': copy.deepcopy(VF_PARAMS),
                'groups': copy.deepcopy(groups)}
    existing = landing.get('native_stage_groups')
    if existing is not None and existing != contract:
        raise ValueError('conflicting native stage-group contract: review explicitly')
    landing['native_stage_groups'] = contract
    return out
