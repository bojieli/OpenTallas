"""Fail-closed parameter preservation for expanded hard leaves.

Signed 32-bit `parameter integer` decimal defaults and unsigned `[31:0]`
literal defaults are supported. Other types/default expressions refuse;
Yosys binary strings retain the explicitly declared parameter signedness.
"""
import hashlib
import json
import re
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class U32(int):
    """An unsigned `parameter [31:0]` value (KV-PARAMS 10-19: ot_qkh_ktree SCALE); never sign-reinterpreted."""


def _u32_literal(text):
    m = re.fullmatch(r"(?:32\s*'\s*([hdb])\s*([0-9a-fA-F_]+)|(\d+))", text)
    if not m:
        return None
    v = int(m[3]) if m[3] else int(m[2].replace('_', ''), dict(h=16, d=10, b=2)[m[1].lower()])
    return v if 0 <= v < (1 << 32) else None


def integer_defaults(source, module):
    text = re.sub(r'//[^\n]*|/\*.*?\*/', '', source, flags=re.S)
    m = re.search(r'\bmodule\s+' + re.escape(module) + r'\s*#\s*\((.*?)\)\s*\(', text, re.S)
    if not m:
        return {}
    result = {}
    kind = None
    for field in m[1].split(','):
        field = field.strip()
        if field.startswith('parameter'):
            if re.match(r'parameter\s+integer\s+', field):
                kind, field = 'int', re.sub(r'^parameter\s+integer\s+', '', field)
            elif re.match(r'parameter\s*\[\s*31\s*:\s*0\s*\]\s*', field):
                # unsigned 32-bit vector with a sized/decimal literal default: the only non-integer form admitted
                kind, field = 'u32', re.sub(r'^parameter\s*\[\s*31\s*:\s*0\s*\]\s*', '', field)
            else:
                kind = None
        p = re.fullmatch(r'(\w+)\s*=\s*(.+)', field)
        if kind == 'int' and p and re.fullmatch(r'-?\d+', p[2]) and -(1 << 31) <= int(p[2]) < (1 << 31):
            value = int(p[2])
        elif kind == 'u32' and p and _u32_literal(p[2].strip()) is not None:
            value = U32(_u32_literal(p[2].strip()))
        else:
            raise ValueError(f'{module}: unsupported parameter declaration {field!r}')
        if p[1] in result:
            raise ValueError(f'{module}: duplicate parameter {p[1]}')
        result[p[1]] = value
    return result


def evaluated(overrides, defaults, module):
    values = dict(defaults)
    literals = {}
    for name, bits in overrides.items():
        if name not in defaults:
            raise ValueError(f'{module}: undeclared/unsupported parameter {name}')
        if not isinstance(bits, str) or not re.fullmatch('[01]{32}', bits):
            raise ValueError(f'{module}.{name}: expected known 32-bit integer, got {bits!r}')
        value = int(bits, 2)
        if bits[0] == '1' and not isinstance(defaults[name], U32):
            value -= 1 << 32
        values[name] = U32(value) if isinstance(defaults[name], U32) else value
        literals[name] = "32'sb" + bits
    return values, literals


def artifact_identity(root, view, rtl):
    vd = (root / view).resolve()
    required = [vd / (vd.name + suffix) for suffix in ('.lef', '_tt.lib', '_ff.lib')]
    required.append(vd / 'insertion.json')
    if any(not p.is_file() for p in required):
        raise ValueError(f'{view}: missing mandatory LEF/TT/FF/insertion artifact')
    # Enumerate exact selected view files: mutable kit spec is intentionally absent.
    return dict(rtl=dict(path=str(rtl), sha256=sha(root / rtl)),
                view=str(view), artifacts={str(p.relative_to(vd)): sha(p) for p in sorted(vd.rglob('*')) if p.is_file()})


def preserve(root, module, overrides, rtl, view, profiles, diagnostic=False):
    defaults = integer_defaults((root / rtl).read_text(), module)
    values, literals = evaluated(overrides, defaults, module)
    if not defaults and not overrides:
        return {}, None
    profile = profiles.get(module)
    if not isinstance(profile, dict):
        raise ValueError(f'{module}: missing selected parameter profile')
    identity = artifact_identity(root, view, rtl)
    if profile.get('identity') != identity or profile.get('parameters') != values:
        raise ValueError(f'{module}: selected parameter profile/source/view mismatch')
    receipt = profile.get('frozen_receipt')
    qualified = False
    if receipt:
        rp = root / receipt['path']
        if sha(rp) != receipt['sha256']:
            raise ValueError(f'{module}: frozen receipt digest mismatch')
        r = json.loads(rp.read_text())
        qualified = (r.get('schema') == 'opentallas.native_parameter_profile.v1' and
                     r.get('identity') == identity and r.get('parameters') == values and
                     r.get('native_qualified') is True)
        if not qualified:
            raise ValueError(f'{module}: frozen receipt lacks matching native qualification')
    if not qualified and not diagnostic:
        raise ValueError(f'{module}: native parameter qualification missing')
    # Include defaults too: later RTL defaults must not silently change this instance.
    literals = {k: "32'sb" + format(v & 0xffffffff, '032b') for k, v in values.items()}
    return literals, dict(parameters=values, identity=identity, native_qualified=qualified,
                          frozen_receipt=receipt)


def verify_bound(root, report, sidecar, actual_instances, leaf_sources, original_instances, diagnostic=False):
    # The proof ledger is not its own census. Enumerate the physical instances
    # against independently configured leaf RTL, including modules whose entry
    # was removed from expand.json. Parameterless legacy leaves need no receipt.
    sources = dict(leaf_sources)
    for module, binding in report.get('leaves', {}).items():
        rtl = binding['rtl']
        if module in sources and sources[module] != rtl:
            raise ValueError(f'{module}: expanded leaf source binding changed')
        sources[module] = rtl
    required = {}
    defaults = {}
    for module, inst, _params, _connections in actual_instances:
        if original_instances.get(inst) == module:
            continue
        if module not in sources:
            continue
        if module not in defaults:
            defaults[module] = integer_defaults((root / sources[module]).read_text(), module)
        if defaults[module]:
            if inst in required:
                raise ValueError(f'{inst}: duplicate actual expanded instance')
            required[inst] = module
    ledger = report.get('parameter_instances', {})
    missing, extra = sorted(set(required) - set(ledger)), sorted(set(ledger) - set(required))
    if missing or extra:
        raise ValueError(f'expanded parameter ledger incomplete: missing={missing}, extra={extra}')
    for inst, row in ledger.items():
        if row['module'] != required[inst]:
            raise ValueError(f'{inst}: expanded parameter instance/master missing or changed')
        expected = row['literals']
        if sidecar.get(inst) != expected:
            raise ValueError(f'{inst}: expanded sidecar missing/conflicting parameters')
        profile = row['profile']
        ident = profile['identity']
        if artifact_identity(root, ident['view'], ident['rtl']['path']) != ident:
            raise ValueError(f'{inst}: expanded source/view artifact changed')
        if not profile['native_qualified'] and not diagnostic:
            raise ValueError(f'{inst}: native parameter qualification missing')
        # Revalidate receipt content as well as its digest: report flags are not proof.
        supplied = dict(profile, identity=ident)
        overrides = {k: v.split("'sb", 1)[1] for k, v in expected.items()}
        literals, checked = preserve(root, row['module'], overrides, ident['rtl']['path'],
                                     ident['view'], {row['module']: supplied}, diagnostic)
        if literals != expected or checked != profile:
            raise ValueError(f'{inst}: expanded profile changed')
