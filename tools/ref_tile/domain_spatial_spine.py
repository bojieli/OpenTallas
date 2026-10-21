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
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('domain_spatial_spine requires exactly the documented fields')
    if type(value['version']) is not int or value['version'] != 1:
        raise ValueError('domain_spatial_spine requires version1')
    if spec.get('clock') != 'multiple_cts_roots':
        raise ValueError('domain_spatial_spine requires multiple_cts_roots')
    for field in ('symmetric', 'rc_cal', 'macro_leaf', 'macro_pin_leaf'):
        if type(value[field]) is not bool:
            raise ValueError(f'domain_spatial_spine {field} must be boolean')
    if value['rc_cal']:
        raise ValueError('domain_spatial_spine requires existing platform RC (rc_cal=false)')
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


def after_entries(spec, root=None):
    if spec.get('domain_spatial_spine') is None:
        return []
    out = [f'source /src/{GUARD}']
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
    plan = record_tap_plan(spec, root) if spec.get('children') else {}
    if plan:
        out += [RECORD_TAPS, 'physical/common_flow/landed_raw_tap.tcl']
        out += [path for row in plan.values() for path in row['files']]
    return out
