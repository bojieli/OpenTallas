#!/usr/bin/env python3
"""Default-OFF, source-pinned packing of the retained TOP227 concat chain.

Only emits a NEW generated C++ file. No compiler, archive, RTL or runtime work.
Socrates owns the changed-TU 513-edge/negative comparison and speed gate.

Verilator 5.050 VL_CONCAT_WWI with rbits=32 and word-aligned lbits writes
out[0]=IData(rhs), out[1:]=left. Its aligned _vl_insert_WW copies every
32-bit word (the full-word mask is all ones). Induction therefore places
append j at final[2047-j], and the original 77824 words at final[2048:].
The final WWW appends four words. All 79872 final words are assigned once;
there are no partial words, padding, arithmetic or rounding changes.

Keep the existing final temporary and VL_ASSIGN_W commit: no state is
written early. Keep VL_SEL_WWII at its original capture point, directed to
the final temporary's disjoint upper range. Keep each RHS expression and
evaluation order verbatim. Remove only dead, single-use intermediate locals.
The complete retained TU hash bounds this transformation to proven source,
not a generic concat optimizer or a future generator/version heuristic.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


SOURCE_SHA256 = 'bea0193fc07e2656367d3e79b0b51fcf160a15e6c198dc7a7cf79ec12428ac0d'
FUNCTION = 'Vdie___024root___nba_sequent__TOP__227'
PREFIX_WORDS = 77824
APPENDS = 2044
FINAL_WORDS = 79872
HELPER_SHA256 = 'd5ded32979d550ffcd00dc12131a805999d8529ad6c45f2ae8b16b343d017f89'
TYPES_SHA256 = 'fa362d371573a489e199eb2ba90775c2e6a03e08e92f9f484ca48ccd55d3299e'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(text, enable=False):
    """Return (source, schema). OFF returns input byte-for-byte via emit()."""
    before = sha(text.encode('utf-8'))
    record = dict(schema='qwen-native-die-linear-pack-v2', enabled=bool(enable),
                  input_sha256=before, function=FUNCTION,
                  verilator_version='5.050', verilated_funcs_sha256=HELPER_SHA256,
                  verilated_types_sha256=TYPES_SHA256,
                  compiled=False, equivalence_gate_pending=True,
                  speed_gate_pending=True, physical_qualified=False)
    if not enable:
        record.update(output_sha256=before, changed=False)
        return text, record
    if before != SOURCE_SHA256:
        raise ValueError('retained 220.cpp source pin mismatch; refuse transformation')
    start = text.index('void ' + FUNCTION + '(')
    # This source-pinned function is the final function in the retained TU.
    body = text[start:]
    if not body.endswith('\n}\n'):
        raise ValueError('TOP227 final function boundary changed')
    capture = re.search(r'^    VL_SEL_WWII\(2490368, 2555904, __Vtemp_31, (vlSelfRef\.\w+), 0U, 2490368\);\n', body, re.M)
    if capture is None:
        raise ValueError('initial aligned capture missing')
    calls = list(re.finditer(
        r'^    VL_CONCAT_WWI\((\d+),(\d+),32, (__Vtemp_\d+), (__Vtemp_\d+), (.*?)\);\n',
        body, re.M | re.S))
    if len(calls) != APPENDS:
        raise ValueError('expected exactly 2044 appends')
    cursor = capture.end()
    # Canonical 5.050 uses opaque handles: raw EData* cannot construct
    # WDataOutP outside its private implementation. The public VlWide&
    # constructor plus operator+(int) selects the same upper words.
    statements = [capture.group().replace(
        '__Vtemp_31,', '(WDataOutP{__Vtemp_30} + 2048),', 1)]
    for j, call in enumerate(calls):
        obits, lbits, dest, left, rhs = call.groups()
        if (call.start() != cursor or int(lbits) != 32 * (PREFIX_WORDS + j)
                or int(obits) != int(lbits) + 32
                or dest != f'__Vtemp_{32+j}' or left != f'__Vtemp_{31+j}'):
            raise ValueError('noncontiguous, misaligned or divergent concat chain')
        # RHS is the original array read/index arithmetic, not an optimizer's
        # re-expression of signed division, casts, shifts or bounds masks.
        if not rhs.startswith('vlSelfRef.') or '__Vtemp_' in rhs:
            raise ValueError('RHS no longer a disjoint state read')
        statements.append(f'    __Vtemp_30[{2047-j}U] = {rhs};\n')
        cursor = call.end()
    trailing = body[cursor:]
    words = re.findall(r'^    __Vtemp_2076\[([0-3])U\] = (vlSelfRef\.\w+\[[0-3]U\]);\n', trailing, re.M)
    if [i for i, _ in words] != ['0', '1', '2', '3']:
        raise ValueError('four-word final append changed')
    for i, rhs in words:
        if not rhs.endswith(f'[{i}U]'):
            raise ValueError('final word ordering changed')
        statements.append(f'    __Vtemp_30[{i}U] = {rhs};\n')
    commit = re.search(r'^    VL_ASSIGN_W\(2555904, (vlSelfRef\.\w+), __Vtemp_30\);\n', trailing, re.M)
    if commit is None or commit.group(1) != capture.group(1):
        raise ValueError('final state commit is not original captured line')
    # Require the complete literal tail: no hidden writes, conditionals or
    # observation of an intermediate temporary between capture and commit.
    expected_tail = ''.join(f'    __Vtemp_2076[{i}U] = {rhs};\n' for i, rhs in words)
    expected_tail += '    VL_CONCAT_WWW(2555904,2555776,128, __Vtemp_30, __Vtemp_2075, __Vtemp_2076);\n'
    expected_tail += commit.group() + '}\n'
    if trailing != expected_tail:
        raise ValueError('unexpected operations in final concat/commit tail')
    replacement = ''.join(statements) + commit.group() + '}\n'
    changed_body = body[:capture.start()] + replacement
    removed_words = 0
    uses = Counter(re.findall(r'\b__Vtemp_\d+\b', changed_body))
    declarations = list(re.finditer(
        r'^    VlWide<(\d+)>/\*\d+:0\*/ (__Vtemp_\d+);\n', changed_body, re.M))
    declared = {m.group(2): m for m in declarations}
    remove = set()
    for n in range(31, 2077):
        name = f'__Vtemp_{n}'
        if name not in declared:
            raise ValueError(f'expected one local declaration: {name}')
        # Check actual liveness after replacement, with token boundaries so
        # __Vtemp_31 cannot spuriously match __Vtemp_310.
        if uses[name] != 1:
            raise ValueError(f'intermediate still observed: {name}')
        removed_words += int(declared[name].group(1))
        remove.add(name)
    changed_body = re.sub(
        r'^    VlWide<(\d+)>/\*\d+:0\*/ (__Vtemp_\d+);\n',
        lambda m: '' if m.group(2) in remove else m.group(), changed_body, flags=re.M)
    output = text[:start] + changed_body
    record.update(changed=True, output_sha256=sha(output.encode('utf-8')),
                  prefix_words=PREFIX_WORDS, append_count=APPENDS,
                  final_words=FINAL_WORDS, retained_temporary='__Vtemp_30',
                  capture_destination='(WDataOutP{__Vtemp_30} + 2048)',
                  append_destination='__Vtemp_30[2047-j] for j=0..2043',
                  final_four_destination='__Vtemp_30[0..3]',
                  removed_temporary_count=2046, removed_temporary_words=removed_words,
                  removed_temporary_bytes=4 * removed_words,
                  concat_helpers_removed=APPENDS + 1,
                  input_bytes=len(text.encode('utf-8')),
                  output_bytes=len(output.encode('utf-8')),
                  state_commit=commit.group().strip(),
                  evaluation_order_preserved=True,
                  rhs_expressions_preserved=True,
                  non_TOP227_source_byte_identical=True)
    return output, record


def patch(text, enable=False):
    return prepare(text, enable)[0]


def emit(source, output, enable=False, schema=None):
    """Exclusive-create output; never overwrite input, output, or a live TU."""
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('output must be a NEW source path')
    if schema is not None and Path(schema).resolve() in (source.resolve(), output.resolve()):
        raise ValueError('schema must have a separate NEW path')
    raw = source.read_bytes()
    transformed, record = prepare(raw.decode('utf-8'), enable)
    result = transformed.encode('utf-8') if enable else raw
    # Preflight schema before creating the source, to avoid partial handoffs.
    if schema is not None and Path(schema).exists():
        raise FileExistsError(schema)
    with output.open('xb') as stream:
        stream.write(result)
    if schema is not None:
        with Path(schema).open('x') as stream:
            json.dump(record, stream, indent=2)
            stream.write('\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--schema', type=Path)
    parser.add_argument('--enable', action='store_true', default=False)
    args = parser.parse_args()
    print(json.dumps(emit(args.input, args.output, args.enable, args.schema), indent=2))
