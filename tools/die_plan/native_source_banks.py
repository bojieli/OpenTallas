"""Opt-in source-identity contract for spatially split native register banks.

The manifest is tied to the original bound body and native wrapper bytes.
Sites follow live_referenced_scalar_ids, never sorted mapped cell names.
"""
import hashlib
import re
from pathlib import Path


def canonical_name(name):
    return name.replace('\\', '').replace('.', '/')


def kit_wrappers(kit_dir, kit_manifest, manifest):
    """Only private, uniquely named kit copies may receive keep attributes."""
    kit_dir = Path(kit_dir).resolve()
    modules = {b['native_array_definition']['module'] for b in manifest.get('banks', [])
               if b.get('source_kind') == 'ARRAY'}
    sources, paths = {}, {}
    definitions = {}
    for filename in kit_manifest['files']:
        path = Path(filename).resolve()
        if path.suffix not in ('.v', '.sv'):
            continue
        body = path.read_text()
        for module in re.findall(r'(?m)^\s*module\s+([A-Za-z_$][\w$]*)\b', body):
            if module in modules:
                definitions.setdefault(module, {})[path] = body
    for module in modules:
        matches = set(definitions.get(module, {}))
        if len(matches) != 1:
            raise ValueError('native source wrapper must be unique in kit manifest: '+module)
        path = matches.pop()
        if not path.is_relative_to(kit_dir):
            raise ValueError('native source wrapper is not kit-local; run kit_rsync.py first: '+module)
        if path.stat().st_nlink != 1:
            raise ValueError('native source wrapper must have a private inode: '+module)
        sources[module] = definitions[module][path]
        paths[module] = path
    return sources, paths


def _integer(token):
    token = token.strip()
    m = re.fullmatch(r"(?:\d+)?'([bdh])([0-9a-fA-F_]+)", token)
    return int(m[2].replace('_', ''), {'b': 2, 'd': 10, 'h': 16}[m[1]]) if m else int(token)


def _rhs_bits(expression):
    """Little-endian literal values, None for variable data; fail unsupported RTL."""
    expression = expression.strip()
    if expression.startswith('{') and expression.endswith('}'):
        result = []
        for term in reversed(expression[1:-1].split(',')):
            result.extend(_rhs_bits(term))
        return result
    literal = re.fullmatch(r"(\d+)'([bdh])([0-9a-fA-F_]+)", expression)
    if literal:
        value = _integer(expression)
        return [(value >> bit) & 1 for bit in range(int(literal[1]))]
    variable = re.fullmatch(r'[\w\\$]+\[(\d+):(\d+)\]', expression)
    if variable:
        return [None] * (abs(int(variable[1])-int(variable[2]))+1)
    raise ValueError('native source constant mask has unsupported driver expression')


def _check_masks(bank, body):
    if not bank.get('constant_masks'):
        return
    definition = bank['native_array_definition']
    pattern = re.escape(definition['register']) + r'\s*\[([^\]]+)\]\s*(?:\[(\d+):(\d+)\])?\s*<=\s*([^;]+);'
    values = {}
    for word, hi, lo, rhs in re.findall(pattern, body):
        word = _integer(word)
        hi, lo = (int(hi), int(lo)) if hi else (definition['width']-1, 0)
        bits = _rhs_bits(rhs)
        if hi < lo or len(bits) != hi-lo+1:
            raise ValueError('native source constant mask driver width mismatch')
        for bit, value in enumerate(bits, lo):
            values.setdefault((word, bit), []).append(value)
    for mask in bank['constant_masks']:
        for lo, hi in mask['ranges']:
            for bit in range(lo, hi+1):
                observed = values.get((mask['word'], bit), [])
                if not observed or any(value != mask['value'] for value in observed):
                    raise ValueError('native source constant mask contradicts actual driver')


def prepare(rows, text, manifest, wrapper_sources, source_sha=None):
    if manifest is None:
        return [], rows
    sha = source_sha or hashlib.sha256(text.encode()).hexdigest()
    if manifest.get('schema') != 'opentallas.native_source_banks.v1' or manifest.get('source_rtl_sha256') != sha:
        raise ValueError('native source manifest schema/source mismatch')
    inventory = {}
    all_scalars = set()
    for bank in manifest.get('banks', []):
        bid = bank['id']
        if bid in inventory or bank.get('source') != 'nativeRTL:'+sha+'#'+bid:
            raise ValueError('native source bank identity/source mismatch')
        scalars = bank['live_referenced_scalar_ids']
        if not scalars or len(scalars) != bank.get('live_referenced_scalar_count'):
            raise ValueError('native source scalar count mismatch')
        normalized = [canonical_name(s) for s in scalars]
        if len(set(normalized)) != len(normalized) or all_scalars.intersection(normalized):
            raise ValueError('native source duplicate scalar ownership')
        all_scalars.update(normalized)
        declaration = bank['actual_register_declaration']
        if bank['source_kind'] == 'ARRAY':
            definition = bank['native_array_definition']
            module = definition['module']
            instance = bank.get('native_instance')
            if not instance or not re.search(r'\b'+re.escape(module)+r'\s+'+re.escape(instance)+r'\s*\(', text):
                raise ValueError('native source actual wrapper instance missing')
            body = wrapper_sources.get(module)
            if body is None or hashlib.sha256(body.encode()).hexdigest() != definition['sha256']:
                raise ValueError('native source wrapper hash mismatch: '+bid)
            if declaration not in body:
                raise ValueError('native source array declaration missing')
            width, words = definition['width'], definition['words']
            declared = re.fullmatch(r'reg\s+\[(\d+):(\d+)\]\s+(\S+)\s+\[(\d+):(\d+)\];', declaration)
            if (not declared or width != abs(int(declared[1])-int(declared[2]))+1
                    or words != abs(int(declared[4])-int(declared[5]))+1
                    or canonical_name(definition['register']) != canonical_name(declared[3])):
                raise ValueError('native source array dimensions/register differ from declaration')
            stem = canonical_name(bank['register_stem'])
            if stem != canonical_name(instance+'/'+declared[3]):
                raise ValueError('native source array scalar stem differs from actual instance')
            expected = {f'{stem}[{w}][{b}]' for w in range(words) for b in range(width)}
            masked = set()
            for mask in bank.get('constant_masks', []):
                if mask.get('value') not in (0, 1) or not 0 <= mask['word'] < words:
                    raise ValueError('native source invalid constant mask')
                for lo, hi in mask['ranges']:
                    if not 0 <= lo <= hi < width:
                        raise ValueError('native source invalid constant range')
                    for bit in range(lo, hi+1):
                        scalar = f"{stem}[{mask['word']}][{bit}]"
                        if scalar in masked:
                            raise ValueError('native source duplicate constant mask')
                        masked.add(scalar)
            if set(normalized) != expected-masked:
                raise ValueError('native source incomplete live/masked array inventory')
            _check_masks(bank, body)
        elif bank['source_kind'] == 'OTHER_REG':
            if declaration not in text or not bank.get('driver_statements') or any(s not in text for s in bank['driver_statements']):
                raise ValueError('native source declaration/driver missing')
            match = re.fullmatch(r'reg\s+\[(\d+):(\d+)\]\s+(\w+)\s*;', declaration)
            if not match:
                raise ValueError('native source unsupported register declaration')
            hi, lo, stem = match.groups()
            expected = {f'{stem}[{b}]' for b in range(min(int(lo), int(hi)), max(int(lo), int(hi))+1)}
            if set(normalized) != expected or bank.get('constant_masks'):
                raise ValueError('native source incomplete scalar inventory')
        else:
            raise ValueError('native source unsupported storage kind')
        inventory[bid] = bank
    selected, ordinary, used = [], [], set()
    for row in rows:
        bank = inventory.get(row['id'])
        if bank is None:
            ordinary.append(row)
            continue
        if row['id'] in used or row['source'] != bank['source'] or len(row['bit_sites_um']) != len(bank['live_referenced_scalar_ids']):
            raise ValueError('native source geometry identity/count mismatch')
        used.add(row['id'])
        selected.append(dict(row, native_scalars=list(bank['live_referenced_scalar_ids'])))
    if used != set(inventory):
        raise ValueError('native source manifest banks lack explicit geometry')
    return selected, ordinary


def preserve(text, manifest, wrapper_sources):
    """Return private annotated body/wrappers; original inputs remain untouched."""
    if manifest is None:
        return text, dict(wrapper_sources)
    wrappers = dict(wrapper_sources)
    seen = set()
    for bank in manifest['banks']:
        declaration = bank['actual_register_declaration']
        if bank['source_kind'] == 'ARRAY':
            module = bank['native_array_definition']['module']
            if module in seen:
                continue
            seen.add(module)
            body = wrappers[module]
            if body.count(declaration) != 1:
                raise ValueError('native source array preservation ambiguous')
            body = body.replace(declaration, '(* keep = 1 *) '+declaration, 1)
            # Wire keep preserves aliases but does not stop identical FF cells
            # merging. Yosys propagates process attributes to generated DFFs.
            body = re.sub(r'(?m)^(\s*)(always\s*@)', r'\1(* keep = 1 *) \2', body)
            wrappers[module] = body
        else:
            if text.count(declaration) != 1:
                raise ValueError('native source register preservation ambiguous')
            text = text.replace(declaration, '(* keep = 1 *) '+declaration, 1)
            for statement in bank['driver_statements']:
                if statement not in text:
                    raise ValueError('native source driver preservation ambiguous')
                text = text.replace(statement, statement.replace('always', '(* keep = 1 *) always', 1), 1)
    return text, wrappers
