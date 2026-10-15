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
                N=512, M=128, geometry_qualification='N/M are target datapath parameters; record dimensions are decoded verbatim. Frozen s4 vectors do not prove unscaled production dimensions.',
                record_count=len(records), cases=cases,
                golden_output_mask_sectors_verified=golden_checks, records=records,
                inter_record_address_dependencies=dependencies, gather_records=sum(r['gather'] for r in records),
                missing_calendar_attributes=sorted(missing), calendar_emitted=False,
                calendar_reason='Exact VM aliases do not determine physical local allocation or actual native capture edges. Inventing latencies would produce another synthetic calendar.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vectors', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.vectors)
    result['decoder_source_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in [
        Path(__file__), ROOT / 'tools/hgi_adapters/su_bench.py', ROOT / 'tools/hgi_sim/records.py',
        ROOT / 'tools/hbm_generic_iface.py', ROOT / 'tools/hgi_sim/machine.py',
        ROOT / 'rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv',
        ROOT / 'tools/hgi_adapters/common.py', ROOT / 'tools/hgi_seq_vectors.py']}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('program', 'record_count', 'gather_records', 'cases', 'golden_output_mask_sectors_verified', 'calendar_emitted')}, indent=2))


if __name__ == '__main__':
    main()
