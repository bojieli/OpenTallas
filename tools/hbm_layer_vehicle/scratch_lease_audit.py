#!/usr/bin/env python3
"""Conservative source footprint/lease audit, without executing any VM values."""
import argparse
import collections
import copy
import hashlib
import json
import sys
from pathlib import Path

VM_END = 262144
SCRATCH = (261120, 262144)


def overlaps(span):
    return max(span[0], SCRATCH[0]) < min(span[1], SCRATCH[1])


def inspect(repo, image, manifest):
    sys.path.insert(0, str(repo / 'tools/hbm_next'))
    from isa_loader import load_isa
    from vm_value_phase import engine_span
    IR, IC = load_isa()
    raw = image.read_bytes()
    records = IC.decode_all(raw)
    meta = json.loads(manifest.read_text())['records']
    assert len(records) == len(meta)
    accesses, dynamic, loops, unions = [], [], [], {}

    def add(index, r, operand, mode, span, kind, **extra):
        assert span[0] <= span[1]
        accesses.append(dict(record=index, operation=r.unit + '.' + r.op,
            operand=operand, mode=mode, span=list(span), kind=kind,
            intersects_scratch=overlaps(span), **extra))

    for index, ((offset, r, rx, encoded), origin) in enumerate(zip(records, meta)):
        assert origin['offset'] == offset and origin['bytes'] == len(encoded)
        if (r.unit, r.op) == ('CTL', 'ENDLOOP'):
            assert loops
            loops.pop()
        if (r.unit, r.op) == ('IDX', 'UNION'):
            shape = (r.desc['A'].m, r.desc['A'].n, r.imm_b, r.imm_a,
                     r.desc['O'].n, r.desc['R'].stride)
            unions[r.desc['R'].base] = dict(record=index, shape=shape,
                count_word=r.desc['D'].base, capacity=r.desc['O'].n)
        if (r.unit, r.op) == ('CTL', 'LOOP'):
            from_vm = bool(r.param & (1 << 17))
            loop = dict(record=index, level=(r.param >> 16) & 1,
                from_VM=from_vm, count_word=r.imm_a if from_vm else None,
                count_max=65535 if from_vm else r.param & 65535)
            if from_vm:
                add(index, r, '__loop_count', 'read', (r.imm_a, r.imm_a + 1), 'implicit_static')
                dynamic.append(dict(record=index, kind='VM_loop_count',
                    count_word=r.imm_a, ISA_count_max=65535,
                    hold='Actual count producer/version and loop bound must be joined.'))
            loops.append(loop)
        active_L = next((x for x in reversed(loops) if x['level'] == 0), None)
        max_L = max(0, active_L['count_max'] - 1) if active_L else 0
        union = unions.get(rx.rtab) if rx and rx.rsel and r.unit != 'ATT' else None
        qualified_union = bool(union and tuple(union['shape']) == (6, 6, 7, 384, 36, 32)
            and active_L and active_L['count_word'] == union['count_word'])
        if rx and rx.rsel:
            if r.unit == 'ATT':
                add(index, r, '__attention_plan', 'read',
                    (rx.rtab, rx.rtab + 32 * IR.PLAN_WORDS), 'implicit_declared_plan')
            else:
                span = (rx.rtab, rx.rtab + IR.TABLE_ROW_WORDS * max_L + rx.n + 1)
                add(index, r, '__row_table', 'read', span, 'unresolved_loop_table')
                conditional = [rx.rtab, rx.rtab + 36 * IR.TABLE_ROW_WORDS] if qualified_union else None
                dynamic.append(dict(record=index, kind='runtime_ROWX_table',
                    rtab=rx.rtab, raw_span=list(span),
                    possible_scratch=overlaps(span), candidate_union=union,
                    conditional_span=conditional,
                    conditional_intersects=overlaps(conditional) if conditional else None,
                    required='Live UNION result with count<=36, rho<6, e=rho*7+kappa with kappa<6; no intervening overwrite. Shape match alone is not value provenance.'))
        # ATT plan mode expands its fixed lanes; expert ROWX remains symbolic.
        if rx and rx.rsel and r.unit != 'ATT':
            expanded = [(None, r)]
        else:
            expanded = IR.expand(r, rx)
        for bank, row in expanded:
            written = IR.written_operands(row)
            for name, d in row.desc.items():
                if d.space != 'VM':
                    continue
                assert d.stride >= 0 and d.istride >= 0, 'signed descriptor stride needs a separate envelope'
                q = copy.deepcopy(row)
                dd = q.desc[name]
                flags = [k for k in ('indexed', 'dyn_mul', 'n_sel', 'lstride', 'l1stride') if getattr(d, k)]
                for k in flags:
                    setattr(dd, k, 0)
                dd.dyn_sel = 0
                lo, hi = engine_span(q, name)
                # SU consumes A's iteration shape for its other operands.
                if row.unit == 'SU' and name in ('B', 'C', 'D', 'O') and 'A' in row.desc:
                    dd.n = max(dd.n, row.desc['A'].n)
                    dd.m = max(dd.m, row.desc['A'].m)
                    lo, hi = engine_span(q, name)
                if (row.unit, row.op) == ('IDX', 'TOPK') and name in ('O','R'):
                    dd.n = max(dd.n, row.param & 4095)
                    dd.m = max(dd.m, row.desc['A'].m)
                    lo, hi = engine_span(q, name)
                if (row.unit, row.op) == ('COLL', 'ROW_GATHER') and name == 'I':
                    hi = max(hi, lo + max(1,(row.imm_a or d.n)-1)*(d.istride or 1)+1)
                if (row.unit, row.op) == ('ARGMAX', 'LOCAL') and name == 'O':
                    hi = max(hi, lo + 2)
                if (row.unit, row.op) == ('COLL', 'ARGMAX_MERGE') and name == 'A':
                    hi = max(hi, lo + 2)
                if row.unit == 'SU' and name == 'R' and row.sut and row.sut.get('red') and 'A' in row.desc:
                    red_count = 1 if (row.sut.get('red_whole') or row.sut.get('red_tree')) else row.desc['A'].m
                    hi = max(hi, lo + max(0,red_count-1)*(d.stride or 1)+1)
                if row.unit == 'IDX' and row.op == 'INDEX' and name in ('C', 'D'):
                    hi = max(hi, lo + d.stride + max(1, d.n))
                conditional = None
                if rx and rx.rsel and row.unit != 'ATT':
                    step = rx.rs.get(name, 0)
                    selector_max = 255 if rx.emask >> IR.OPND.index(name) & 1 else 15 - rx.slot0
                    shift = selector_max * step
                    lo += min(0, shift)
                    hi += max(0, shift)
                    if qualified_union:
                        selector_max = 40 if rx.emask >> IR.OPND.index(name) & 1 else 5
                        c0, c1 = engine_span(q, name)
                        shift = selector_max * step
                        conditional = [c0 + min(0, shift), c1 + max(0, shift)]
                    flags.append('runtime_ROWX_selector')
                if flags and 'runtime_ROWX_selector' not in flags:
                    # No runtime value is guessed. Indexed legal VM accesses
                    # may extend to the end of VM, even if expected IDs are small.
                    raw_span = [max(0, min(lo, VM_END)), VM_END]
                    if d.lstride or d.l1stride or d.dyn_mul < 0:
                        raw_span = [0,VM_END]
                    expected = None
                    if row.unit == 'SU' and name == 'A' and d.indexed and d.dyn_mul == 1:
                        expected = [lo, hi + 383]
                    dynamic.append(dict(record=index, slot=bank, operand=name,
                        kind='dynamic_VM_descriptor', flags=flags,
                        descriptor=str(d), raw_legal_VM_span=raw_span,
                        possible_scratch=overlaps(raw_span),
                        conditional_expert384_span=expected,
                        conditional_intersects=overlaps(expected) if expected else None,
                        index_to_hit_scratch=[SCRATCH[0] - hi + 1, SCRATCH[1] - lo - 1],
                        hold='Need actual producer/value version and range guard through spills; expected expert IDs<384 are a contract, not inferred memory contents.'))
                    add(index, row, name, 'write' if name in written else 'read',
                        raw_span, 'unresolved_dynamic_VM', slot=bank)
                else:
                    add(index, row, name, 'write' if name in written else 'read',
                        (lo, hi), 'unresolved_ROWX_selector' if flags else 'declared_static',
                        slot=bank, conditional_span=conditional,
                        conditional_intersects=overlaps(conditional) if conditional else None)
                # HBM indexed/n-from-VM consumers also implicitly read I+L.
                if name == 'I' and any(x.indexed or x.n_sel == 63 for x in row.desc.values()):
                    stream_rows = max(1, row.desc.get('O', d).m) if (row.unit, row.op) == ('DMA', 'LOAD') else 1
                    add(index, row, '__I_plus_L', 'read', (d.base, d.base + max_L + stream_rows),
                        'implicit_I_stream', conditional_span=[d.base,d.base+36] if qualified_union else None)
                    if any(x.n_sel == 63 for x in row.desc.values()):
                        add(index, row, '__I_count_plus_L', 'read',
                            (d.base+d.stride,d.base+d.stride+max_L+1),'implicit_I_count')
                if row.unit == 'SU' and row.sut and row.sut.get('c_pair') and name == 'A':
                    add(index, row, '__c_pair', 'read', (max(0, lo - 1), hi + 1), 'implicit_partner_envelope')
                if (row.unit, row.op) == ('COLL', 'ROW_GATHER') and name == 'A':
                    dynamic.append(dict(record=index, kind='ROW_GATHER_selected_row',
                        descriptor=str(d), possible_scratch=True,
                        hold='Actual selected row IDs, owner mapping and resident row-store bounds required; descriptor.m alone does not bound selected row IDs.'))
        if (r.unit, r.op) == ('CTL', 'END'):
            assert not loops
    direct = [x for x in accesses if x['intersects_scratch'] and x['kind'] in
              ('declared_static', 'implicit_static', 'implicit_declared_plan', 'implicit_partner_envelope')]
    unresolved = [x for x in accesses if x['intersects_scratch'] and x not in direct]
    return dict(status='CONSERVATIVE_SOURCE_AUDIT_NOT_A_RESERVATION',
        image_sha256=hashlib.sha256(raw).hexdigest(), commands=len(records),
        scope='Target262144-word physical VM; all records/predicates inspected, declared envelopes are conservative; larger ISA address ABI is not allocated memory.',
        scratch_global_words=list(SCRATCH), scratch_SID=3, scratch_local_words=[64512,65536],
        concrete_declared_intersections=direct,
        declared_static_high_water_exclusive=max(x['span'][1] for x in accesses if x['kind']=='declared_static'),
        access_counts_by_kind=dict(collections.Counter(x['kind'] for x in accesses)),
        unresolved_intersections=unresolved,
        dynamic_inputs=dynamic,
        scratch_reserved=False, runtime_or_golden_replayed=False,
        allocator_contract=['Reserve [261120,262144) with effective cap261120 across all phases and indirect operands; recompile/recheck the complete programme.',
            'No DMA.LOAD output, arithmetic output, table, loop counter, implicit I+L or selected gather may alias the lease.',
            'Prove UNION/INDEX/TOPK range and live value provenance through real spill writes/returns; no data-dependent values invented here.',
            'Each slot is owned before staging until true WB ACK and all readers retire; dates and actual producer still pending.',
            'Declared envelope exclusion does not establish actual source binding, whole-programme liveness or a COPY route.'],
        normative=['tools/hgi_sim/machine.py:eff/vm_addrs/loop_count',
            'tools/hbm_next/isa_v1r_20261019/hbm_next/isa_rows.py:table_entries/expand/idx_union',
            'tools/hbm_next/vm_value_phase.py:engine_span'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for k in ('repo','image','manifest','out'):
        p.add_argument('--'+k, type=Path, required=True)
    a = p.parse_args()
    result = inspect(a.repo,a.image,a.manifest)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.exists():
        raise ValueError('Fresh result required')
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','commands','declared_static_high_water_exclusive','access_counts_by_kind','scratch_reserved')}))
    print('concrete_declared_intersections',len(result['concrete_declared_intersections']))
    print('unresolved_intersections',len(result['unresolved_intersections']))
    print('dynamic_inputs',len(result['dynamic_inputs']))
