#!/usr/bin/env python3
"""Decode frozen2197-bit SU dispatches; inventory actual addresses, never infer cycles."""
import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/hgi_adapters'))
import su_bench as SB
from hgi_sim.records import MDesc


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs(values):
    answer = []
    for value in sorted(values):
        if answer and answer[-1][1] + 1 == value:
            answer[-1][1] = value
        else:
            answer.append([value, value])
    return answer


def masks(addresses):
    result = {}
    for address in addresses:
        sector, bit = divmod(address, 8)
        result[sector] = result.get(sector, 0) | (1 << bit)
    return result


def mask_runs(addresses):
    result = []
    for sector, mask in sorted(masks(addresses).items()):
        if result and result[-1][1] + 1 == sector and result[-1][2] == mask:
            result[-1][1] = sector
        else:
            result.append([sector, sector, mask])
    return result


def summary(addresses):
    ordered = sorted(addresses)
    return dict(words=len(ordered), ranges=runs(ordered),
                address_sha256=hashlib.sha256(b''.join(a.to_bytes(4, 'little') for a in ordered)).hexdigest(),
                sector_mask_runs=mask_runs(ordered))


def decode(raw):
    assert 0 <= raw < 1 << 2197, 'record width'
    d = dict(hdr=raw & ((1 << 128) - 1), sut=(raw >> 128) & ((1 << 256) - 1),
             eff=[(raw >> (384 + 256 * k)) & ((1 << 256) - 1) for k in range(7)],
             n=[raw >> 2176] + [0] * 6)
    assert SB.pack_rec(d) == raw, 'dispatch roundtrip'
    unit = SB.C.fld(d['hdr'], 'unit', SB.C.UOP)
    if unit == 3:
        d = SB.sfu_as_su(d)
        assert d is not None, 'SFU cannot lower to SU'
    kind, _ = SB.ref_word(d)
    assert kind in (0, 1), 'record refused by adapter contract'
    present = SB.C.fld(d['hdr'], 'opnd', SB.C.UOP)
    return d, unit, SB.sut_fields(d['sut']), {
        name: MDesc.decode(d['eff'][k]) for k, name in enumerate('ABCDORI') if present >> k & 1}


def inventory(directory):
    files = ['su_rec.mem', 'su_case.mem', 'su_price.mem', 'su_prod.json', 'su_sizes.svh']
    manifest = json.loads((directory / 'su_prod.json').read_text())
    raw = [int(s, 16) for s in (directory / files[0]).read_text().split()]
    prices = [int(s, 16) / 10 for s in (directory / files[2]).read_text().split()]
    assert len(raw) == len(prices) == len(manifest['cases'])
    records, outputs, sources = [], [], []
    missing = set()
    for index, value in enumerate(raw):
        dispatch, unit, sut, desc = decode(value)
        original_header = value & ((1 << 128) - 1)
        original_present = SB.C.fld(original_header, 'opnd', SB.C.UOP)
        original_descriptors = {name: dataclasses.asdict(MDesc.decode((value >> (384 + 256 * k)) & ((1 << 256) - 1)))
                                for k, name in enumerate('ABCDORI') if original_present >> k & 1}
        no, ni = desc['A'].m, dispatch['n'][0]
        needed = {'A'}
        if sut['m1'] in (1, 4, 6) or sut['ad'] == 3 or sut['e2'] == 1:
            needed.add('B')
        if sut['m2'] == 1 or sut['qm'] or sut['ad'] in (1, 2) or sut['e1'] in (1, 2):
            needed.add('A' if sut['c_pair'] else 'C')
        if sut['qm'] or sut['ad'] == 5:
            needed.add('D')
        if sut['a_ind']:
            needed.add('I')
            missing.add('gather index VM contents at actual execution edge')
        role_addresses, roles = {}, {}
        for name, md in desc.items():
            ist = 0 if md.ibcast else (md.istride or 1)
            used = name in needed or (name == 'O' and sut['dst']) or (name == 'R' and sut['red'])
            addrs = set()
            exact = md.space == 'VM' and not (name == 'A' and sut['a_ind'])
            if used and exact:
                if name == 'R':
                    count = 1 if sut['red_whole'] or sut['red_tree'] else no
                    addrs = {(md.base + row * (md.stride or 1)) % (1 << 24) for row in range(count)}
                elif name == 'I':
                    count = ni if sut['a_ind'] == 1 else no
                    addrs = {(md.base + i) % (1 << 24) for i in range(count)}
                else:
                    addrs = {(md.base + o * md.stride + ((i >> 1) if name in 'BD' and sut['b_half'] else i) * ist) % (1 << 24)
                             for o in range(no) for i in range(ni)}
                    if name == 'A' and sut['c_pair']:
                        addrs |= {a ^ 1 for a in addrs}
            role_addresses[name] = addrs
            roles[name] = dict(descriptor=dataclasses.asdict(md), used=bool(used), exact=exact,
                               effective_inner_stride=ist, inner_broadcast=bool(md.ibcast),
                               row_broadcast=md.stride == 0 and no > 1,
                               half_index=bool(name in 'BD' and sut['b_half']),
                               **summary(addrs))
            if any(a >= 1 << 18 for a in addrs):
                missing.add('address exceeds D1 2^18-word VM aperture')
        src = set().union(*(role_addresses.get(k, set()) for k in needed))
        out = set().union(*(role_addresses.get(k, set()) for k in ('O', 'R')))
        outputs.append(out)
        sources.append(src)
        span_words = {k: (max(a) // 8 - min(a) // 8 + 1) * 8 for k, a in role_addresses.items() if a}
        overlaps = []
        keys = list(role_addresses)
        for pos, a in enumerate(keys):
            for b in keys[pos + 1:]:
                common = role_addresses[a] & role_addresses[b]
                if common:
                    overlaps.append(dict(roles=[a, b], words=len(common), ranges=runs(common)))
        records.append(dict(index=index, tag=manifest['cases'][index]['tag'], original_unit=unit,
                            original_present_descriptors=original_descriptors,
                            effective_n=ni, effective_m=no, elements=ni * no, sut=sut,
                            model_price=prices[index], gather=bool(sut['a_ind']),
                            reduction=dict(kind=sut['red'], whole=sut['red_whole'], tree=sut['red_tree'], square=sut['red_sq']),
                            roles=roles, exact_role_aliases=overlaps, output=summary(out),
                            local_capacity=dict(frame_words=65536, frames=4, total_words=262144,
                                                sector_rounded_span_words_by_role=span_words,
                                                sum_separate_role_spans=sum(span_words.values()),
                                                unique_live_vm_words_lower_bound=len(src | out),
                                                minimum_frames_if_separate_spans=sum((v + 65535) // 65536 for v in span_words.values()),
                                                allocation_fit_proven=False)))
    cases = []
    for line in (directory / 'su_case.mem').read_text().split():
        fields = [int(line[i:i + 8], 16) for i in range(0, 56, 8)]
        first, count, _, _, first_out, count_out, case_id = fields
        assert first + count <= len(raw)
        combined = set().union(*outputs[first:first + count])
        cases.append(dict(case_id=case_id, first_record=first, records=count,
                          first_output_sector=first_out, output_sectors=count_out,
                          output_words=len(combined), summed_model_price=sum(prices[first:first + count])))
    # The frozen vectors carry independent golden written-word masks. Verify the
    # decoded record address coverage against them, including partial sink guards.
    golden_checks = 0
    if all((directory / f).exists() for f in ('su_vmg.mem', 'su_vme.mem')):
        files += ['su_vmg.mem', 'su_vme.mem']
        gm = [int(s, 16) for s in (directory / 'su_vmg.mem').read_text().split()]
        ge = [int(s, 16) >> 256 for s in (directory / 'su_vme.mem').read_text().split()]
        assert len(gm) == len(ge)
        for case in cases:
            first, count = case['first_record'], case['records']
            actual = masks(set().union(*outputs[first:first + count]))
            start, end = case['first_output_sector'], case['first_output_sector'] + case['output_sectors']
            expected = dict(zip(ge[start:end], gm[start:end]))
            assert actual == expected, f'golden output mask mismatch case{case["case_id"]}'
            golden_checks += len(expected)
    dependencies = []
    for later, src in enumerate(sources):
        for earlier in range(later):
            common = outputs[earlier] & src
            if common:
                dependencies.append(dict(producer=earlier, consumer=later, words=len(common), ranges=runs(common),
                                         note='address overlap; intervening writers must be resolved before forwarding'))
    missing.update(['actual datapath issue/commit/capture latencies for each operation',
                    'compiler-selected local frame/bump allocation and source replication mapping',
                    'fixed native bank port assignment and operand gather/broadcast schedule',
                    'fixed drain completion and frame-release edges'])
    return dict(status='actual frozen record/address inventory; no static-cycle calendar qualification',
                program=manifest['program'], source_files={str(directory / f): sha(directory / f) for f in files},
                N=512, M=128, geometry_qualification='N/M are target datapath parameters; record dimensions are decoded verbatim. Canonical descriptor comparison is required to establish unscaled program geometry.',
                record_count=len(records), cases=cases,
                golden_output_mask_sectors_verified=golden_checks, records=records,
                inter_record_address_dependencies=dependencies, gather_records=sum(r['gather'] for r in records),
                missing_calendar_attributes=sorted(missing), calendar_emitted=False,
                calendar_reason='Exact VM aliases do not determine physical local allocation or actual native capture edges. Inventing latencies would produce another synthetic calendar.')



def canonical_dispatches(model, ds_program=None):
    from hgi_sim import records as SR
    if model == 'qwen':
        words, recs, _, _ = SB.C.SV.qwen_program()
        trace, _ = SB.C.qwen_dispatch()
    else:
        program = json.loads(ds_program.read_text())
        words, recs = [], []
        for entry in program['layers'][0]['records']:
            payload = bytes.fromhex(entry['hex'])
            record, _ = SR.decode_one(payload, 0)
            record.tag = entry['tag']
            recs.append(record)
            words += [int.from_bytes(payload[q:q + 16], 'little') for q in range(0, len(payload), 16)]
        words += SB.C.SV.record(SB.C.SV.header('CTL', 'END'), descs={'A': SB.C.SV.mdesc(space=1, fmt=5, base=(1 << 18) - 16, n=1, m=1)})
        trace, _ = SB.C.SV.Ref(words, 0, 0, (1 << 20) - 1, 0, 129280, 1 << 20, {}).run()
    by_pc, pc = {}, 0
    for record in recs:
        by_pc[pc] = record
        pc += SR.rec_bytes(record) // 16
    answer = {}
    for dispatch in trace:
        record = by_pc.get(dispatch['rec'])
        if record and record.unit in ('SU', 'SFU') and record.tag not in answer:
            answer[record.tag] = dispatch
    return answer


def compare_canonical(result, model, ds_program=None):
    canonical = canonical_dispatches(model, ds_program)
    details = []
    for record in result['records'][:result['cases'][0]['records']]:
        expected = canonical.get(record['tag'])
        if expected is None:
            details.append(dict(index=record['index'], tag=record['tag'], missing_canonical=True))
            continue
        _, _, _, descriptors = decode(SB.pack_rec(expected))
        differences = []
        actual = record['original_present_descriptors']
        for role in set(actual) | set(descriptors):
            target = dataclasses.asdict(descriptors[role]) if role in descriptors else None
            present = actual.get(role)
            if target != present:
                differences.append(dict(role=role, fields={key: dict(actual=(present or {}).get(key), canonical=(target or {}).get(key))
                    for key in set(present or {}) | set(target or {}) if (present or {}).get(key) != (target or {}).get(key)}))
        if record['effective_n'] != expected['n'][0]:
            differences.append(dict(effective_n=dict(actual=record['effective_n'], canonical=expected['n'][0])))
        details.append(dict(index=record['index'], tag=record['tag'], differences=differences))
    return dict(model=model, all_included_record_geometries_match=all(not d.get('missing_canonical') and not d['differences'] for d in details),
                included_records=details,
                canonical_SU_SFU_tags_absent_from_included_program=sorted(set(canonical) - {r['tag'] for r in result['records']}),
                qualification='Descriptor geometry comparison; absent units, numerical program execution and hardware cycle scheduling remain separate')



def compare_geometry(full, reduced):
    by_tag = {r['tag']: r for r in reduced['records']}
    answer = []
    for record in full['records']:
        other = by_tag.get(record['tag'])
        changes = []
        if other is None:
            answer.append(dict(tag=record['tag'], absent_from_reduced=True))
            continue
        for key in ('effective_n', 'effective_m'):
            if record[key] != other[key]:
                changes.append(dict(field=key, full=record[key], reduced=other[key]))
        for role in set(record['original_present_descriptors']) | set(other['original_present_descriptors']):
            a = record['original_present_descriptors'].get(role, {})
            b = other['original_present_descriptors'].get(role, {})
            for field in set(a) | set(b):
                if a.get(field) != b.get(field):
                    changes.append(dict(role=role, field=field, full=a.get(field), reduced=b.get(field)))
        answer.append(dict(index=record['index'], tag=record['tag'], descriptor_changes=changes))
    return dict(records=answer, changed_records=sum(bool(r.get('descriptor_changes')) for r in answer),
                qualification='Exact field differences; no uniform compression or numerical equivalence assumed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vectors', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--canonical', choices=('qwen', 'deepseek'))
    parser.add_argument('--compare-vectors', type=Path)
    parser.add_argument('--ds-program', type=Path, default=ROOT / 'results/arch/hgi_programs_20261010/inputs/ds_rank0_program.json')
    args = parser.parse_args()
    result = inventory(args.vectors)
    if args.compare_vectors:
        reduced = inventory(args.compare_vectors)
        result['reduced_vector_comparison'] = compare_geometry(result, reduced)
        result['reduced_vector_source_sha256'] = reduced['source_files']
    if args.canonical:
        result['canonical_comparison'] = compare_canonical(result, args.canonical, args.ds_program)
    result['decoder_source_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in [
        Path(__file__), ROOT / 'tools/hgi_adapters/su_bench.py', ROOT / 'tools/hgi_sim/records.py',
        ROOT / 'tools/hbm_generic_iface.py', ROOT / 'tools/hgi_sim/machine.py',
        ROOT / 'rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv',
        ROOT / 'tools/hgi_adapters/common.py', ROOT / 'tools/hgi_seq_vectors.py']}
    if args.canonical:
        extra = [ROOT / 'tools/hgi_sim/qwen_compiler.py', ROOT / SB.C.SV.G.MODELS['qwen3_8b']['cfg']] if args.canonical == 'qwen' else [args.ds_program]
        result['canonical_source_sha256'] = {str(p): sha(p) for p in extra}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('program', 'record_count', 'gather_records', 'cases', 'golden_output_mask_sectors_verified', 'calendar_emitted')}, indent=2))


if __name__ == '__main__':
    main()
