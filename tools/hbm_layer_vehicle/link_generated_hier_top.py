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
        return int(text)
    match = re.fullmatch(r"(\d*)'([sS]?)([bBoOdDhH])([0-9a-fA-F]+)", text)
    if not match:
        raise ValueError('nonliteral parameter: ' + text)
    width, signed, radix, digits = match.groups()
    value = int(digits, {'b': 2, 'o': 8, 'd': 10, 'h': 16}[radix.lower()])
    if signed and width and value >= 1 << (int(width) - 1):
        raise ValueError('signed negative parameter requires typed resolution: ' + text)
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


def defaults(body):
    head = re.match(r'module\s+\w+\s*', body)
    at = head.end()
    if body[at] != '#':
        return {}
    start = body.index('(', at)
    params = {}
    for item in split(body[start + 1:close(body, start)]):
        left, sep, value = item.partition('=')
        name = re.search(r'(\w+)\s*$', left)
        if not sep or not name:
            raise ValueError('nondefault parameter declaration ' + item[:100])
        params[name[1]] = literal(value)
    return params


def unescape(name):
    return re.sub(r'__0([0-9A-Fa-f]{2})', lambda m: chr(int(m[1], 16)), name)


def prepare(preprocessed, top_text, args_text, stub_root, output):
    original = modules(preprocessed)
    topmods = modules(top_text)
    if len(topmods) != 1:
        raise ValueError('exactly one top required')
    topname, top = next(iter(topmods.items()))
    if norm(top) != norm(original[topname]):
        raise ValueError('raw top differs from selected preprocessed top')
    if re.search(r'\b(always|initial|assign|function|task|generate)\b', top):
        raise ValueError('top is not pure connectivity')
    variants, stubs, rows = {}, {}, []
    for line in args_text.splitlines():
        if line.endswith('.sv') and not line.startswith('/'):
            path = stub_root / line
            text = path.read_text()
            declarations = modules(text)
            if len(declarations) != 1 or 'Wrapper module for DPI protected library' not in text:
                raise ValueError('not a generated DPI wrapper: ' + str(path))
            name, body = next(iter(declarations.items()))
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
                params[key] = literal(value)
            variants.setdefault(source, []).append((target, params))
    edits = []
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
            overrides = {k: literal(v) for k, v in named(top[start + 1:parameter_end - 1]).items()}
            at = parameter_end
        tail = re.match(r'\s*(\w+)\s*\(', top[at:])
        if not tail:
            raise ValueError('unsupported top instance after ' + source)
        instance = tail[1]
        start = at + tail.end() - 1
        end = close(top, start)
        ports = named(top[start + 1:end])
        params = defaults(original[source])
        if not overrides.keys() <= params.keys():
            raise ValueError('unknown instance override ' + instance)
        params.update(overrides)
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
    output.mkdir(parents=True, exist_ok=False)
    output.joinpath('linked_top.sv').write_text('`timescale 1ns/1fs\n' + linked + '\n')
    used = sorted({row['dpi_module'] for row in rows})
    output.joinpath('source.f').write_text('\n'.join(stubs[x]['path'] for x in used) + '\n' + str(output / 'linked_top.sv') + '\n')
    receipt = dict(status='PREP_STRUCTURAL_PARAMETER_AND_PORT_JOIN_ONLY', native_child_bodies_changed=0,
                   top=topname, instances=rows, instance_count=instance_count, used_dpi_modules=len(used),
                   emitted_connectivity_reread='EXACT_MATCH',
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
    result = prepare(a.preprocessed.read_text(), a.top.read_text(), a.args.read_text(), a.stub_root, a.out)
    print(json.dumps({k: result[k] for k in ('status', 'instance_count', 'used_dpi_modules')}))
