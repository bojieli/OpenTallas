"""Source-owned spatial distribution of already declared CTS domains.

This option changes the physical implementation of existing roots only. Timing,
relationships, landing checks and post-CTS signoff remain with clock entries.
"""
import hashlib
import math
from pathlib import Path
import re

ENGINE = 'physical/common_flow/clock_spine.tcl'
ENGINE_SHA256 = '6f6b9f1c7b4466b6ae72ee2faa398ecdd6fa76b73445758843b1488f671113a5'
ENGINE_BALANCING_BASE_SHA256 = 'aab59f9a4f61ffbbaefa56c611d6793f1e3e59e40e256506de269ed902fd7d83'
GUARD = 'physical/common_flow/domain_spatial_spine.tcl'
PG_BINDING = 'physical/common_flow/native_pg_binding.tcl'
RECORD_TAPS = 'physical/common_flow/spine_record_taps.tcl'
CHILD_INS = 'physical/common_flow/domain_spine_child_ins.tcl'
CHILD_INS_MODES = ('boundary_record',)


def record_tap_plan(spec, root):
    """Derive fixed hybrid-raw targets from the existing CLOSED child records."""
    if spec.get('domain_spatial_spine') is None or not spec.get('children'):
        return {}
    import clock_entry_constraints as C
    root = Path(root)
    targets = C.landed_tap_targets(spec, root)
    if not targets:
        return {}
    plan = {}
    source_keys = set()
    for child in spec['children']:
        view = root / child['view']
        relevant = {key: row for key, row in targets.items()
                    if key.startswith(view.name + '/')}
        if not relevant:
            continue
        record = C.landed_record_pins(view, root)
        if record['model'] != 'hybrid':
            raise ValueError('staged record taps support only existing hybrid_raw records')
        instance = child.get('inst', '')
        if child.get('count', 1) != 1 or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', instance):
            raise ValueError('staged record taps require one exact source child instance')
        for key, row in relevant.items():
            raw = key.split('/', 1)[1]
            if raw not in record['raw']:
                raise ValueError('staged tap is not an existing record-signed raw pin')
            paths = [row['record'], row['verdict'], child['view'] + '/insertion.json']
            paths += [child['view'] + '/' + view.name + suffix
                      for suffix in ('.lef', '_tt.lib', '_ff.lib', '_ss.lib')]
            hashes = {}
            for path in paths:
                relative = Path(path)
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('staged tap source must be inside the source snapshot')
                hashes[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
            identity = instance + '/' + raw
            if identity in plan or key in source_keys:
                raise ValueError('duplicate staged raw terminal/source target')
            source_keys.add(key)
            plan[identity] = dict(instance=instance, master=view.name, raw=raw,
                                  ref=row['ref'], source_key=key,
                                  owner_rule='same_declared_root',
                                  targets={corner: row[corner] for corner in ('tt', 'ff', 'ss')},
                                  files=hashes)
    if {row['source_key'] for row in plan.values()} != set(targets):
        raise ValueError('staged plan does not cover every existing landed target')
    return plan


def child_insertion_targets(spec, root):
    """SQ-TTC4 10-21 (Q.STA.TTC.4, landed-regions standard: a parent root is judged at the CHILD FLOPS, TT and FF <= 80):
    {"<master>/<clock pin>": TT ps} = the hard child's own insertion from its CLOSED record, on exactly the basis the gate
    judges (pre_route_gate.root_child_flops): clock_measurements[pin].tt.boundary.mean of a CTS-root pin, the child's
    tt.boundary.mean when it has one clock pin and no per-pin record, the leaf pin -> SRAM wire mean (landed_raw_pins
    refs) of a raw entry.  The per-domain spine balances every hard-child clock-pin leaf at pin arrival + this value, so
    the child's boundary flops arrive WITH the root's soft flops (safe12c / LRT fixture: ck_core wtn R 141.6 -> span
    149.2, ck_hr ck_head R 303.1 -> span 363.2 when the pin itself is balanced).  Fail closed on a missing record."""
    import json
    import clock_entry_constraints as C
    root = Path(root)
    out = {}
    for child in spec.get('children') or []:
        view = root / child['view']
        ins = json.loads((view / 'insertion.json').read_text())
        cm = ins.get('clock_measurements') or {}
        lib = (view / f'{view.name}_tt.lib').read_text(errors='replace')
        clocks = sorted(pin for pin, body in C._lib_pin_blocks(lib).items() if re.search(r'clock\s*:\s*true', body))
        if not clocks:
            raise ValueError(f'child_insertion: {view.name} has no Liberty clock pin')
        raw = None
        for pin in clocks:
            row = cm.get(pin) if cm else None
            b = ((row or {}).get('tt') or {}).get('boundary') if cm else (ins.get('tt') or {}).get('boundary')
            if cm and row is None:
                raise ValueError(f'child_insertion: {view.name}/{pin} has no clock_measurements record')
            if not cm and len(clocks) != 1:
                raise ValueError(f'child_insertion: {view.name} has {len(clocks)} clock pins but no per-pin record')
            if b and b.get('n') and b.get('mean') is not None:
                value = float(b['mean'])
            else:
                if raw is None:
                    raw = C.landed_raw_pins(view, root)
                if pin not in raw:
                    raise ValueError(f'child_insertion: {view.name}/{pin} has neither a boundary nor a raw record')
                value = float(raw[pin]['refs']['tt'][1])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'child_insertion: {view.name}/{pin} insertion {value} not a finite non-negative ps')
            out[f'{view.name}/{pin}'] = round(value, 1)
    if not out:
        raise ValueError('child_insertion requires hard children')
    return out


def _tcl(value):
    if isinstance(value, dict):
        return '[dict create ' + ' '.join(_tcl(k) + ' ' + _tcl(v)
                                          for k, v in value.items()) + ']'
    value = str(value)
    if any(c in value for c in '{}\\\n\r'):
        raise ValueError('unsupported staged-record literal')
    return '{' + value + '}'


def validate(spec, domains, root):
    value = spec.get('domain_spatial_spine')
    if value is None:
        return None
    fields = {'version', 'roots', 'symmetric', 'bin_um', 'leaf_max', 'iterations',
              'rc_cal', 'macro_leaf', 'macro_pin_leaf'}
    # SQ-TTC4 10-21: optional 'child_insertion' (absent = every existing kit byte-identical)
    if not isinstance(value, dict) or set(value) - {'child_insertion'} != fields:
        raise ValueError('domain_spatial_spine requires exactly the documented fields')
    if type(value['version']) is not int or value['version'] != 1:
        raise ValueError('domain_spatial_spine requires version1')
    if spec.get('clock') != 'multiple_cts_roots':
        raise ValueError('domain_spatial_spine requires multiple_cts_roots')
    for field in ('symmetric', 'rc_cal', 'macro_leaf', 'macro_pin_leaf'):
        if type(value[field]) is not bool:
            raise ValueError(f'domain_spatial_spine {field} must be boolean')
    # SQC-CTLM 10-22: rc_cal=true balances the spine on the RCX-calibrated clock RC (clock_spine.tcl OT_SPINE_RC_CAL, 594825ff5).
    # With rc_cal=false the CTMS ctlm spines (safe15-17) were balanced on platform RC (C 0.145 vs RCX 0.10 fF/um):
    # ck_hr pin-flop spread 58 ps at CTS grew to 155-260 TT / 99-187 FF at GRT.  Requires the RC-cal helper.
    if value['rc_cal'] and not (Path(root) / 'tools/orfs_hold_mm.tcl').is_file():
        raise ValueError('domain_spatial_spine rc_cal=true requires the RC-cal helper tools/orfs_hold_mm.tcl')
    if value['macro_pin_leaf'] and not value['macro_leaf']:
        raise ValueError('macro_pin_leaf requires macro_leaf')
    for field, lo, hi in [('leaf_max', 1, 32), ('iterations', 1, 20)]:
        if type(value[field]) is not int or not lo <= value[field] <= hi:
            raise ValueError(f'domain_spatial_spine {field} outside {lo}..{hi}')
    number = value['bin_um']
    if type(number) not in (int, float) or not math.isfinite(number) or not 1 <= number <= 500:
        raise ValueError('domain_spatial_spine bin_um outside1..500')
    roots = value['roots']
    if not isinstance(roots, list) or not roots:
        raise ValueError('domain_spatial_spine roots must be an explicit nonempty list')
    expected = []
    for port in spec['clock_ports']:
        owners = [name for name, d in domains.items() if port in d['ports']]
        if len(owners) != 1 or domains[owners[0]]['ports'] != [port]:
            raise ValueError('domain_spatial_spine requires one existing root per exclusive domain')
        expected.append(dict(domain=owners[0], port=port))
    if roots != expected:
        raise ValueError('domain_spatial_spine roots must exactly match existing clock_ports/domain ownership in order')
    # A dual-clock raw memory owns distinct physical clock contacts, not one leaf
    # per macro. The shell's six contacts must never collapse to three leaves.
    dual = any(len(binding.get('clock_pins', {})) > 1
               for binding in spec.get('soft_root_macro_bindings', {}).values())
    if dual and not (value['macro_leaf'] and value['macro_pin_leaf']):
        raise ValueError('dual-clock raw memories require macro_leaf and macro_pin_leaf')
    if 'child_insertion' in value:
        if value['child_insertion'] not in CHILD_INS_MODES:
            raise ValueError(f'domain_spatial_spine child_insertion must be one of {CHILD_INS_MODES}')
        if not (value['macro_leaf'] and value['macro_pin_leaf'] and value['symmetric']):
            raise ValueError('child_insertion requires macro_leaf, macro_pin_leaf and symmetric (one leaf per hard-child '
                             'clock pin, tapped early by the symmetric builder)')
        # the targets themselves are derived (fail closed) by after_entries/dependencies from the kit's source root
        if not (Path(root) / CHILD_INS).is_file():
            raise ValueError('domain_spatial_spine child-insertion helper missing')
    path = Path(root) / ENGINE
    if hashlib.sha256(path.read_bytes()).hexdigest() != ENGINE_SHA256:
        raise ValueError('domain_spatial_spine canonical engine differs from reviewed staged-phase bytes')
    if not (Path(root) / GUARD).is_file():
        raise ValueError('domain_spatial_spine ownership guard missing')
    return value


def before_entries(spec):
    """Install engine inside the existing entries/landing wrapper, not around it."""
    value = spec.get('domain_spatial_spine')
    if value is None:
        return []
    # The explicit schema owns these knobs. A daemon environment cannot inject
    # an ICG traversal, alternate cell, rest tree or unreviewed balancing policy.
    out = ['# Explicit per-domain spatial spine; existing clock-entry timing is unchanged.',
           'foreach name [array names ::env OT_SPINE*] {unset ::env($name)}']
    knobs = dict(PORTS=','.join(r['port'] for r in value['roots']),
                 SYM=int(value['symmetric']), RC_CAL=0, BIN=value['bin_um'],
                 LEAF_N=value['leaf_max'], ITERS=value['iterations'],
                 MACRO_LEAF=int(value['macro_leaf']),
                 MACRO_PIN_LEAF=int(value['macro_pin_leaf']))
    out += [f'set ::env(OT_SPINE_{key}) {{{val}}}' for key, val in knobs.items()]
    out += [f'set ::ot_dsp_roots {{{" ".join(r["port"] for r in value["roots"])}}}',
            f'source /src/{ENGINE}']
    return out


def child_insertion_tcl(spec, root):
    """after the engine: the per-pin child-insertion dict + the fixed leaf-arrival wrapper ([] without the option)"""
    value = spec.get('domain_spatial_spine')
    if value is None or 'child_insertion' not in value:
        return []
    targets = child_insertion_targets(spec, root)
    return ['# SQ-TTC4 10-21: hard-child clock-pin leaves balanced at pin + the child record insertion (child flops)',
            'set ::ot_sp_child_ins ' + _tcl(targets),
            f'source /src/{CHILD_INS}']


def after_entries(spec, root=None):
    if spec.get('domain_spatial_spine') is None:
        return []
    out = child_insertion_tcl(spec, root) + [f'source /src/{GUARD}']
    plan = record_tap_plan(spec, root) if spec.get('children') else {}
    if plan:
        out += ['set ::ot_sp_record_taps_v1 ' + _tcl(dict(version=1, model='hybrid_raw', records=plan)),
                f'source /src/{RECORD_TAPS}']
    return out


def dependencies(spec, root=None):
    # The reviewed engine sources PG binding in ordinary mode too. Preserve
    # that transitive input even when the surrounding kit is not pg_strict.
    if spec.get('domain_spatial_spine') is None:
        return []
    out = [ENGINE, GUARD, PG_BINDING]
    if 'child_insertion' in spec['domain_spatial_spine']:
        out += [CHILD_INS]
        out += [f"{ch['view']}/insertion.json" for ch in spec.get('children') or []]
        out += [f"{ch['view']}/{Path(ch['view']).name}_tt.lib" for ch in spec.get('children') or []]
    plan = record_tap_plan(spec, root) if spec.get('children') else {}
    if plan:
        out += [RECORD_TAPS, 'physical/common_flow/landed_raw_tap.tcl']
        out += [path for row in plan.values() for path in row['files']]
    return out
