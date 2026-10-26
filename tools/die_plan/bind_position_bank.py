"""Effective consumer timing of the opt-in KV uniform position-ID landing bank.

The wrappers preserve the original slg ABI and contain the same 52 kept data
flops everywhere. These are the existing declared stack/group IDs; no delay or
phase selector is added. RTL proof/model lives in kv_pc_r8_position_bank_1025.
"""
import re

ABI = 'kv_pc_r8_position_bank_v1'
WRAPPERS = {'kv3_pc': 'qkd_kvs_grp_h_r2c_r8pos', 'kv3_pc_v1': 'qkd_kvs_grp_r2c_r8pos'}


def decode(stack, group, port):
    if port == 'x__tok':
        return 2 if stack == 3 and group in (2, 3, 4, 6) else 0
    if port == 'x__tep':
        return 1 if stack == 2 and group == 1 else 0
    raise ValueError(f'not a position-bank port: {port}')


def spec(b, ci, port):
    if getattr(b, 'ab', {}).get('position_banks') != ABI or port not in ('x__tok', 'x__tep'):
        return None
    c = b.F.cells[ci]
    part = b.cpart.get(ci)
    tn = b.parts[part]['type'] if part in b.parts else None
    # clock-landing cohorts (clock_landing_plan.compose) keep their base plan type's physical template
    tn = b.plan['partition_types'].get(tn, {}).get('landing_base_type', tn) if tn else tn
    if tn not in WRAPPERS:
        return None
    if c.module != WRAPPERS[tn]:
        return None
    m = re.fullmatch(r'slg_(WS|WN|ES|EN)_([0-6])', c.path)
    if not m:
        raise ValueError(f'position bank has no declared physical ID: {c.path}')
    stack, group = ('WS', 'WN', 'ES', 'EN').index(m[1]), int(m[2])
    if (tn == 'kv3_pc') != (group == 4):
        raise ValueError(f'{c.path}: position group does not match physical template {tn}')
    width = 18 if port == 'x__tok' else 16
    if len(c.ports[port]) != width or len(c.ports.get('slg__cfg_stack', [])) != 2 or len(c.ports.get('slg__cfg_group', [])) != 3:
        raise ValueError(f'{c.path}: position bank ABI width mismatch')
    return dict(abi=ABI, port=port, stack=stack, group=group, pad=decode(stack, group, port),
                max_depth=2 if port == 'x__tok' else 1, width=width,
                selector='existing_slg_cfg_stack_and_cfg_group')


def extra(b, ci, port):
    x = spec(b, ci, port)
    return x['pad'] if x else 0


def layout(b):
    mode = getattr(b, 'ab', {}).get('position_banks')
    wrapped = [c for c in b.F.cells if c.module in WRAPPERS.values()]
    if mode is None:
        if wrapped:
            raise ValueError('position-bank wrapper is present without its timing declaration')
        return None
    if mode != ABI:
        raise ValueError(f'unknown position-bank declaration {mode}')
    cells = []
    for ci, c in enumerate(b.F.cells):
        s = spec(b, ci, 'x__tok')
        if s:
            cells.append(dict(inst=c.path, partition=b.cpart[ci], module=c.module,
                              stack=s['stack'], group=s['group'],
                              token_cycles=s['pad'], epoch_cycles=decode(s['stack'], s['group'], 'x__tep')))
    if len(cells) != 28:
        raise ValueError(f'position-bank cohort has {len(cells)} replicas, expected 28')
    return dict(abi=ABI, instances=cells, kept_flops_per_instance=52, kept_flops_total=52*len(cells),
                new_partition_pins=0, arbitrary_delay_selectors=0)


def physical_key(meta, landed_pad):
    if meta.get('abi') != ABI or meta.get('selector') != 'existing_slg_cfg_stack_and_cfg_group':
        raise ValueError('unknown position-bank implementation')
    port = meta['port']
    maximum, width = (2, 18) if port == 'x__tok' else (1, 16) if port == 'x__tep' else (-1, -1)
    if meta.get('max_depth') != maximum or meta.get('width') != width:
        raise ValueError('position-bank physical shape mismatch')
    if type(meta.get('stack')) is not int or type(meta.get('group')) is not int or not 0 <= meta['stack'] < 4 or not 0 <= meta['group'] < 7:
        raise ValueError('position-bank ID outside declared physical positions')
    expected = decode(meta['stack'], meta['group'], port)
    if meta.get('pad') != expected or landed_pad != expected:
        raise ValueError('position-bank timing differs from its declared position-ID decode')
    return (ABI, port, maximum, width)
