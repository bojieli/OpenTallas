"""Generate distinct OPEN LP parent sources using the CLOSED CPR Q contract.

This is source binding, with no inherited parent closure or gate qualification.
The actual CPR physical export is supplied separately by its owning lane.
"""
import argparse
import json
import re
from pathlib import Path
from frame_bind import source_text

Q = 'ot_v41_rom_elem_q_qxpq_w10'
RECEIPT = 'results/rtl/dsrom_qelem_pq_20261006/qxpq_cpr_1019/closed/receipt.json'


def receipt_params(receipt):
    args = receipt['driver_args']
    return dict(args[i+1].split('=', 1) for i, x in enumerate(args) if x == '--param')


def emit(text, old, new, params):
    # Match only Q parameter lists. INSTANCE contains a concatenation, so parse
    # balanced parentheses rather than ending at its inner close parenthesis.
    start = 0
    parts = []
    count = 0
    for m in re.finditer(r'\b' + Q + r'\s*#\s*\(', text):
        pos = m.end(); depth = 1
        while depth:
            if text[pos] == '(': depth += 1
            elif text[pos] == ')': depth -= 1
            pos += 1
        original = text[m.end():pos-1]
        inst = re.search(r'\.INSTANCE\((.*)\)\s*$', original)
        if not inst:
            raise ValueError('Q binding must retain its exact INSTANCE expression')
        numeric = dict(re.findall(r'\.(\w+)\((\d+)\)', original))
        if set(numeric) - set(params):
            raise ValueError('Q source has a parameter absent from the closed receipt')
        replacement = ', '.join(f'.{k}({v})' for k, v in params.items())
        replacement += ', .INSTANCE(' + inst.group(1) + ')'
        parts += [text[start:m.end()], replacement, ')']
        start = pos; count += 1
    if count != 12:
        raise ValueError(f'expected actual twelve Q hard children, found {count}')
    parts.append(text[start:])
    result = ''.join(parts)
    result = re.sub(r'\bmodule\s+' + old + r'\b', 'module ' + new, result, count=1)
    return ('// OPEN CPR LP parent: CLOSED Q leaf contract cc0ec1c19 only.\n'
            '// Requires OT_XS_Q_CPR=1; Q launch advances one edge, BF unchanged.\n' + result), count


def overlay(table, source_ref, paths, export=None):
    """Opt in an already explicit72 table; parent views remain unqualified."""
    import copy
    out = copy.deepcopy(table)
    for h in (9, 10):
        old = f'col_h{h}_l4_lp'; new = old + '_cpr'
        for m in out['masters'].values():
            if m.get('module') == old:
                m.update(module=new, view=None, view_note='OPEN CPR LP parent; non-CPR closure does not apply.')
        for key in ('rtl_widths', 'standin_pin_plans'):
            out.setdefault(key, {})[new] = copy.deepcopy(out[key][old])
        # Never reuse the non-CPR physical kit as a CPR parent qualification.
        out.setdefault('kits', {}).pop(new, None)
    for entry in out.get('frame_lp_binding', {}).get('instances', {}).values():
        entry['module'] += '_cpr'
    out.setdefault('rtl_refs', {})[source_ref] = list(paths)
    out['prefer'] = [f'{source_ref}/{p}' for p in paths] + out.get('prefer', [])
    out['frame_cpr_binding'] = dict(parent_status='OPEN', leaf_closure_record='cc0ec1c19',
        receipt=RECEIPT, compiler_env={'OT_XS_Q_CPR':'1'}, q_launch_advance_edges=1,
        bf_launch_advance_edges=0, source_ref=source_ref, export=export,
        physical_export_status='SUPPLIED' if export else 'PENDING',
        inherited_non_cpr_parent_closure=False)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-ref', default='21b97190e')
    ap.add_argument('--receipt-ref', default='1bb4ee3e3')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    params = receipt_params(json.loads(source_text(a.receipt_ref, RECEIPT)))
    if params.get('CPR') != '1' or params.get('RSTP') != '1':
        raise ValueError('requires exact CLOSED CPR receipt')
    a.out.mkdir(parents=True, exist_ok=True)
    record = dict(source_ref=a.source_ref, receipt_ref=a.receipt_ref, receipt=RECEIPT,
                  params=params, closure_record='cc0ec1c19', parent_status='OPEN',
                  compiler_env={'OT_XS_Q_CPR':'1'}, parents={})
    for h in (9, 10):
        old = f'col_h{h}_l4_lp'; new = old + '_cpr'
        path = f'rtl/dsrom_sys/s81_dv/frame_lp/{old}_rf3r.sv'
        text, count = emit(source_text(a.source_ref, path), old, new, params)
        target = a.out / (new + '.sv'); target.write_text(text)
        record['parents'][new] = dict(source=str(target), q_children=count,
            old_source=path, instance_identity='unchanged', physical_closure='OWED')
    (a.out / 'binding.json').write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    main()
