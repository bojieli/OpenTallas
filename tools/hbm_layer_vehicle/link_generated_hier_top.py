#!/usr/bin/env python3
"""Link a pure connectivity top to its exact Verilator-generated DPI variants.

This is a simulation packaging transform. It consumes an already completed child
frontend inventory; it does not replace a child with a behavioural approximation.
Unknown parameters, ambiguous variants and incomplete port inventories fail closed.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def clean(text):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)


def norm(text):
    return re.sub(r'\s+', '', clean(text))


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def close(text, start):
    assert text[start] == '('
    depth = 0
    for at in range(start, len(text)):
        depth += (text[at] == '(') - (text[at] == ')')
        if not depth:
            return at
    raise ValueError('unbalanced parentheses')


def split(text):
    result, begin, depth = [], 0, 0
    for at, char in enumerate(text):
        if char in '({[':
            depth += 1
        elif char in ')}]':
            depth -= 1
        elif char == ',' and depth == 0:
            result.append(text[begin:at].strip())
            begin = at + 1
    result.append(text[begin:].strip())
    return result


def literal(text):
    text = norm(text).replace("\\'", "'").replace('_', '')
    if re.fullmatch(r'-?\d+', text):
        value = int(text)
        if not -(1 << 31) <= value < (1 << 31):
            raise ValueError('explicit width required for large unsized decimal')
        return value
    match = re.fullmatch(r"(\d*)'([sS]?)([bBoOdDhH])([0-9a-fA-F]+)", text)
    if not match:
        raise ValueError('nonliteral parameter: ' + text)
    width, signed, radix, digits = match.groups()
    value = int(digits, {'b': 2, 'o': 8, 'd': 10, 'h': 16}[radix.lower()])
    if not width and value >= 1 << 32:
        raise ValueError('explicit width required for large unsized based literal')
    width = int(width) if width else 32
    if not 1 <= width <= 4096:
        raise ValueError('unsupported literal width')
    value &= (1 << width) - 1
    if signed and value >= 1 << (width - 1):
        value -= 1 << width
    return value


def named(text):
    result = {}
    for item in split(text):
        match = re.fullmatch(r'\.\s*(\w+)\s*\((.*)\)', item, re.S)
        if not match or match[1] in result:
            raise ValueError('not a unique named connection: ' + item[:100])
        result[match[1]] = norm(match[2])
    return result


def modules(text):
    text = clean(text)
    result = {}
    for match in re.finditer(r'\bmodule\s+(\w+)\b', text):
        end = re.search(r'\bendmodule\b', text[match.end():])
        if not end:
            raise ValueError('module without endmodule')
        body = text[match.start():match.end() + end.end()]
        if match[1] in result:
            raise ValueError('duplicate module ' + match[1])
        result[match[1]] = body
    return result


def typed(value, formal):
    text = norm(value)
    if text in ("'0", "'1"):
        bits = 0 if text == "'0" else (1 << formal['width']) - 1
    else:
        bits = literal(text) & ((1 << formal['width']) - 1)
    return dict(type=formal, bits=bits)


def defaults(body):
    head = re.match(r'module\s+\w+\s*', body)
    at = head.end()
    if body[at] != '#':
        return {}
    start = body.index('(', at)
    params, formal = {}, None
    for item in split(body[start + 1:close(body, start)]):
        left, sep, value = item.partition('=')
        name = re.search(r'(\w+)\s*$', left)
        if not sep or not name:
            raise ValueError('nondefault parameter declaration ' + item[:100])
        prefix = left[:name.start()].strip()
        if prefix:
            prefix = re.sub(r'^parameter\s*', '', prefix).strip()
            if prefix == 'integer':
                formal = dict(kind='integer', width=32, signed=True)
            else:
                packed = re.fullmatch(r'\[\s*(\d+)\s*:\s*(\d+)\s*\]', prefix)
                if not packed:
                    raise ValueError('unsupported formal type; require fixed packed range or integer: ' + item[:100])
                msb, lsb = map(int, packed.groups())
                formal = dict(kind='packed', width=abs(msb - lsb) + 1, signed=False, msb=msb, lsb=lsb)
        if formal is None:
            raise ValueError('untyped parameter is unsupported: ' + item[:100])
        params[name[1]] = typed(value, formal)
    return params


def apply_override(params, key, value):
    if key not in params:
        raise ValueError('unknown parameter: ' + key)
    params[key] = typed(value, params[key]['type'])


def file_identity(path):
    stat = path.stat()
    return (stat.st_size, stat.st_ino, stat.st_mtime_ns // 10**9, stat.st_mtime_ns % 10**9,
            stat.st_ctime_ns // 10**9, stat.st_ctime_ns % 10**9)


def cache_source_guard(stubs, source_path, preprocessed, original, compiled):
    source_path = source_path.resolve()
    if source_path.read_text() != preprocessed:
        raise ValueError('cache source path does not contain the selected preprocessed bytes')
    actual = file_identity(source_path)
    result, child_args_hashes = {}, {}
    for name, stub in stubs.items():
        metadata = Path(stub['path']).parent / ('V' + name + '__verFiles.dat')
        wrapper = Path(stub['path']).resolve()
        child_args = wrapper.parent.parent / ('V' + name + '__hierMkArgs.f')
        args_stat = child_args.stat()
        if max(args_stat.st_ctime_ns, args_stat.st_mtime_ns) > metadata.stat().st_mtime_ns:
            raise ValueError('child arguments changed after frontend: ' + name)
        source_module, expected_params = compiled[name]
        params = defaults(original[source_module])
        for line in child_args.read_text().splitlines():
            if line.strip().startswith('-G'):
                key, sep, value = line.strip()[2:].partition('=')
                if not sep:
                    raise ValueError('unsupported child parameter override: ' + line)
                apply_override(params, key, value)
        if params != expected_params:
            raise ValueError('parent variant disagrees with cached child arguments: ' + name)
        rows, outputs, commands = [], [], []
        for line in metadata.read_text().splitlines():
            fields = line.split('"')
            if line.startswith('S ') and len(fields) >= 4 and Path(fields[3]).resolve() == source_path:
                rows.append(tuple(map(int, fields[0].split()[1:])))
            if line.startswith('T ') and len(fields) >= 4 and Path(fields[3]).resolve() == wrapper:
                outputs.append(tuple(map(int, fields[0].split()[1:])))
            if line.startswith('C ') and len(fields) >= 2:
                commands.append(fields[1])
        if rows != [actual]:
            raise ValueError('cached child source epoch differs: ' + name)
        if outputs != [file_identity(wrapper)]:
            raise ValueError('generated DPI wrapper changed after frontend: ' + name)
        if commands != ['-f ' + str(child_args)]:
            raise ValueError('unsupported cached child command: ' + name)
        result[name] = digest(metadata.read_text())
        child_args_hashes[name] = digest(child_args.read_text())
    return dict(status='PASS_EXACT_CACHED_SOURCE_PATH_AND_FILE_IDENTITY', source_path=str(source_path),
                source_sha256=digest(preprocessed), source_stat=list(actual), child_metadata_sha256=result,
                compiled_child_arguments_sha256=child_args_hashes,
                dpi_outputs_and_compiled_parameters='EXACT_MATCH')


def unescape(name):
    return re.sub(r'__0([0-9A-Fa-f]{2})', lambda m: chr(int(m[1], 16)), name)


def prepare(preprocessed, top_text, args_text, stub_root, output, *, source_path):
    original = modules(preprocessed)
    topmods = modules(top_text)
    if len(topmods) != 1:
        raise ValueError('exactly one top required')
    topname, top = next(iter(topmods.items()))
    if any('"' in body or '\\' in body for body in (top, original[topname])):
        raise ValueError('quoted strings and escaped identifiers are unsupported in connectivity tops')
    if norm(top) != norm(original[topname]):
        raise ValueError('raw top differs from selected preprocessed top')
    if re.search(r'\b(always|initial|assign|function|task|generate|defparam|bind|specify|if|for|case)\b', top):
        raise ValueError('top is not pure connectivity')
    if re.search(r'(?m)^\s*(?:input|output|inout|wire|logic|reg|bit)\b[^;]*=', top):
        raise ValueError('declaration initializers are unsupported')
    top_head = re.match(r'module\s+\w+\s*\(', top)
    if not top_head:
        raise ValueError('parameterized or unsupported top header')
    header_end = close(top, top_head.end() - 1)
    if '=' in top[:header_end] or not re.match(r'\s*;', top[header_end + 1:]):
        raise ValueError('unsupported top port declaration')
    header_end = top.index(';', header_end)
    variants, stubs, rows = {}, {}, []
    for line in args_text.splitlines():
        if line.endswith('.sv') and not line.startswith('/'):
            path = stub_root / line
            text = path.read_text()
            declarations = modules(text)
            if len(declarations) != 1 or 'Wrapper module for DPI protected library' not in text:
                raise ValueError('not a generated DPI wrapper: ' + str(path))
            name, body = next(iter(declarations.items()))
            if name in stubs:
                raise ValueError('duplicate generated DPI module: ' + name)
            ports = set(re.findall(r'\b(?:input|output|inout)\s+(?:logic|wire|reg)?\s*(?:\[[^]]+\])?\s*(\w+)', body))
            stubs[name] = dict(path=str(path), sha256=digest(text), ports=ports)
        if line.startswith('--hierarchical-block '):
            fields = line.split(None, 1)[1].split(',')
            if len(fields) % 2:
                raise ValueError('malformed hierarchical parameter mapping')
            source, target = unescape(fields[0]), fields[1]
            params = defaults(original[source])
            for key, value in zip(fields[2::2], fields[3::2]):
                if key not in params:
                    raise ValueError('unknown hierarchy parameter: ' + key)
                apply_override(params, key, value)
            variants.setdefault(source, []).append((target, params))
    compiled = {}
    for source, entries in variants.items():
        for target, params in entries:
            if target in compiled:
                raise ValueError('duplicate hierarchy target: ' + target)
            compiled[target] = (source, params)
    if compiled.keys() != stubs.keys():
        raise ValueError('generated wrapper and hierarchy variant inventories differ')
    edits, instance_ranges = [], []
    instance_count = 0
    for match in re.finditer(r'^\s*(\w+)\s*(?=#|\w)', top, re.M):
        source = match[1]
        if source not in variants:
            continue
        at = match.end()
        parameter_start = parameter_end = None
        overrides = {}
        if top[at] == '#':
            parameter_start = at
            start = top.index('(', at)
            parameter_end = close(top, start) + 1
            overrides = named(top[start + 1:parameter_end - 1])
            at = parameter_end
        tail = re.match(r'\s*(\w+)\s*\(', top[at:])
        if not tail:
            raise ValueError('unsupported top instance after ' + source)
        instance = tail[1]
        start = at + tail.end() - 1
        end = close(top, start)
        if not re.match(r'[ \t\r\n]*;[ \t\r]*(?:\n|$)', top[end + 1:]):
            raise ValueError('require exactly one instance per declaration and line: ' + instance)
        instance_ranges.append((match.start(1), top.index(';', end) + 1))
        ports = named(top[start + 1:end])
        params = defaults(original[source])
        if not overrides.keys() <= params.keys():
            raise ValueError('unknown instance override ' + instance)
        for key, value in overrides.items():
            apply_override(params, key, value)
        candidates = [(target, p) for target, p in variants[source] if p == params]
        if len(candidates) != 1:
            raise ValueError(f'{instance}: expected one exact parameter variant, found {len(candidates)}')
        target = candidates[0][0]
        if target not in stubs or ports.keys() != stubs[target]['ports']:
            raise ValueError('DPI port inventory mismatch: ' + instance)
        edits.append((match.start(1), match.end(1), target))
        if parameter_start is not None:
            edits.append((parameter_start, parameter_end, ''))
        rows.append(dict(instance=instance, source_module=source, dpi_module=target,
                         effective_parameters=params, port_graph_sha256=digest(json.dumps(ports, sort_keys=True))))
        instance_count += 1
    # A pure top must not contain a second, unhandled module instance.
    all_calls = re.findall(r'^\s*(\w+)\s*(?:#\s*\([^;]*?\)\s*)?\w+\s*\(', top, re.M)
    all_calls = [x for x in all_calls if x != 'module']
    if instance_count != len(all_calls):
        raise ValueError(f'unhandled top instances: linked {instance_count}, source {len(all_calls)}')
    residue = top
    for start, end in sorted(instance_ranges, reverse=True):
        residue = residue[:start] + ' ' * (end - start) + residue[end:]
    residue = residue[header_end + 1:residue.rfind('endmodule')]
    residue = re.sub(r'\b(?:input|output|inout|wire)\b[^;]*;', '', residue)
    if residue.strip():
        raise ValueError('unsupported non-declaration/non-instance top body: ' + residue.strip()[:80])
    linked = top
    for start, end, replacement in sorted(edits, reverse=True):
        linked = linked[:start] + replacement + linked[end:]
    # Independently read the emitted calls back. All connected expressions and
    # instance names must survive exactly; only types and resolved parameters move.
    reread = {}
    for match in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\(', linked, re.M):
        target, instance = match.groups()
        if target not in stubs:
            continue
        start = match.end() - 1
        ports = named(linked[start + 1:close(linked, start)])
        if instance in reread:
            raise ValueError('duplicate emitted instance ' + instance)
        reread[instance] = (target, digest(json.dumps(ports, sort_keys=True)))
    expected = {row['instance']: (row['dpi_module'], row['port_graph_sha256']) for row in rows}
    if reread != expected:
        raise ValueError('emitted connectivity graph differs from frozen top')
    cache_guard = cache_source_guard(stubs, source_path, preprocessed, original, compiled)
    output.mkdir(parents=True, exist_ok=False)
    output.joinpath('linked_top.sv').write_text('`timescale 1ns/1fs\n' + linked + '\n')
    used = sorted({row['dpi_module'] for row in rows})
    output.joinpath('source.f').write_text('\n'.join(stubs[x]['path'] for x in used) + '\n' + str(output / 'linked_top.sv') + '\n')
    receipt = dict(status='PREP_STRUCTURAL_PARAMETER_AND_PORT_JOIN_ONLY', native_child_bodies_changed=0,
                   top=topname, instances=rows, instance_count=instance_count, used_dpi_modules=len(used),
                   emitted_connectivity_reread='EXACT_MATCH',
                   cache_source_guard=cache_guard,
                   original_top_sha256=digest(top_text), preprocessed_sha256=digest(preprocessed),
                   original_args_sha256=digest(args_text), linked_top_sha256=digest(output.joinpath('linked_top.sv').read_text()),
                   wrapper_sha256={x: stubs[x]['sha256'] for x in used})
    output.joinpath('receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--preprocessed', type=Path, required=True)
    ap.add_argument('--top', type=Path, required=True)
    ap.add_argument('--args', type=Path, required=True)
    ap.add_argument('--stub-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    result = prepare(a.preprocessed.read_text(), a.top.read_text(), a.args.read_text(), a.stub_root, a.out,
                     source_path=a.preprocessed)
    print(json.dumps({k: result[k] for k in ('status', 'instance_count', 'used_dpi_modules')}))
