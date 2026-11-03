"""Validate exact native hard-cell bindings before typed parent-LEC stubs.

This preserves content parameters. It proves neither the hard-cell arithmetic
nor asset contents; those remain the selected child view's obligations.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

SCHEMA = 'opentallas.lec_native_stub_metadata.v1'
CONTRACT = 'lec_native_stub_metadata.json'


def _native_bb():
    path = Path(__file__).with_name('native_bb.py')
    spec = importlib.util.spec_from_file_location('lec_native_bb_defaults', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _file(kit, name):
    path = (Path(kit) / name).resolve()
    if not path.is_relative_to(Path(kit).resolve()) or not path.is_file():
        raise ValueError('native metadata input missing/outside kit: ' + name)
    return path


def load(kit):
    path = Path(kit) / CONTRACT
    c = json.loads(path.read_text())
    if c.get('schema') != SCHEMA or not c.get('bindings') or not c.get('headers'):
        raise ValueError('missing typed native stub metadata contract')
    if not c.get('source_hashes') or not c.get('top'):
        raise ValueError('native stub contract must pin selected source and top')
    for group in ['headers', 'source_hashes']:
        for name, digest in c[group].items():
            got = hashlib.sha256(_file(kit, name).read_bytes()).hexdigest()
            if got != digest:
                raise ValueError('native stub selected input changed: ' + name)
    defaults = _native_bb().headers_params([_file(kit, n) for n in c['headers']])
    masters = {v['master'] for v in c['bindings'].values()}
    if not masters.issubset(defaults):
        raise ValueError('native stub master has no exact typed header')
    return c, defaults


def _string_equal(actual, expected):
    # Yosys emits an empty string as either empty or one padded space. No
    # nonempty content label is normalized, truncated, or case-folded.
    return actual in ('', ' ') if expected == '' else actual == expected


def validate(data, contract, defaults):
    """Check actual hierarchical gold cells against every selected binding."""
    native_bb = _native_bb()
    expected = contract['bindings']
    masters = {v['master'] for v in expected.values()}
    modules = data['modules']
    def is_top(value):
        return (isinstance(value, int) and value != 0) or (isinstance(value, str)
                and bool(value) and set(value) <= {'0', '1'} and int(value, 2) != 0)
    actual_tops = [name for name, module in modules.items()
                   if is_top(module.get('attributes', {}).get('top'))]
    if actual_tops != [contract['top']]:
        raise ValueError('native contract must name the unique actual elaborated top')
    records = {}

    def walk(module_name, prefix, stack):
        if module_name in stack or module_name not in modules:
            raise ValueError('invalid elaborated native hierarchy: ' + module_name)
        module = modules[module_name]
        for name, cell in module.get('cells', {}).items():
            path = prefix + name
            master = cell['type']
            if master in masters:
                want = expected.get(path)
                if want is None or want['master'] != master:
                    raise ValueError('unexpected native binding: ' + path)
                params = cell.get('parameters', {})
                typed = defaults[master]
                if 'INSTANCE' in typed:
                    if typed['INSTANCE'][0] != 'str' or 'content_label' not in want:
                        raise ValueError('missing typed native content identity: ' + path)
                    actual = params.get('INSTANCE', typed['INSTANCE'][1])
                    if not _string_equal(actual, want['content_label']):
                        raise ValueError('wrong native INSTANCE: ' + path)
                for key, value in params.items():
                    kind, default = typed.get(key, ('unknown', None))
                    if key == 'INSTANCE':
                        if kind != 'str':
                            raise ValueError('unsupported INSTANCE parameter: ' + path)
                    elif kind == 'int':
                        if not native_bb.bits_equal(value, default):
                            raise ValueError('native parameter differs from selected header: ' + path + '.' + key)
                    elif kind == 'str':
                        if not _string_equal(value, default):
                            raise ValueError('unsupported native string override: ' + path + '.' + key)
                    else:
                        raise ValueError('unsupported native parameter: ' + path + '.' + key)
                records[path] = {'master': master, 'parameters': params,
                                 'content_label': want.get('content_label')}
            elif master in modules and not modules[master].get('attributes', {}).get('blackbox'):
                walk(master, path + '.', stack + (module_name,))

    walk(contract['top'], '', ())
    if set(records) != set(expected):
        raise ValueError('missing selected native bindings: ' + repr(sorted(set(expected) - set(records))))
    # Only exact header defaults become declarations. Unknown parameters are
    # absent, and every observed override was checked before these are used.
    declarations = {}
    for master in masters:
        declarations[master] = {p: (kind, value) for p, (kind, value) in defaults[master].items()
                                if kind in ('int', 'str')}
    return declarations, {'schema': SCHEMA, 'verdict': 'PASS', 'top': contract['top'], 'bindings': records,
                          'qualification': 'selected source/parameter identities only; hard-cell arithmetic unchanged'}


def check(kit, elaborated, receipt):
    c, defaults = load(kit)
    declarations, report = validate(json.loads(Path(elaborated).read_text()), c, defaults)
    Path(receipt).write_text(json.dumps(report, indent=2) + '\n')
    return declarations
