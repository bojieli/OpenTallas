"""Explicit, byte-sealed ROMQ parent source preparation; no plan adoption.

Replace selected native NB=2 calls with the proved registered split shell before
fixed-child assembly. INSTANCE expressions and all accepted logical parameters
remain in the parent; only the sealed NB=2 parameter loses its override because
the shell has exactly two halves. Physical child sealing is a later operation.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from kit_assembly import _instance_type_spans, _named_overrides, _masked_rtl, _literal_integer

MASTER = 'ot_v41_rom_elem_q_qxpq_w10_gb'
SHELL = MASTER + '_shell'
def recipe_cgr():
    """CGR of the ROM-element hard core = the legacy recipe params over its spec (gen_core_kit_legacy.py order)."""
    root = Path(__file__).resolve().parents[2] / 'physical/die_plan/s81/cores/legacy'
    rec = json.loads((root / 'recipes.json').read_text())['ot_v41_rom_elem_q_qxpq_w10']
    spec = json.loads((root.parents[4] / rec['ref_tile'] / 'spec.json').read_text()) if rec.get('ref_tile') else {}
    return int(dict((spec.get('params') or {}), **(rec.get('params') or {})).get('CGR', 0))


RECIPE_CGR = recipe_cgr()
# CGR 0 stays accepted only for parents already sealed with it (the signed _he / _hw halves, S81-ROMQ-B4 11-06);
# a new contract selects the recipe value so the shell matches the CGR the child is built with.
LEGACY_CGR = 0
ALLOWED_CGR = {LEGACY_CGR, RECIPE_CGR}
FIXED = dict(CGR=RECIPE_CGR, EARLY=1, FAST=1, FRONT_PAR=0, MTP=1, NB=2,
             PP=1, PQ=1, QM=5, QPIPE=1, QP_CAP=0, QP_CSAM=10,
             QP_P1=1, QP_XS=1, QS=5, QTIMING_FIX=1, QW=0,
             QX=10, QY=1, QZ=1, QZ_NE=4, QZ_NS=8, RSTP=1,
             GO_BOUNDARY=1, IFN=1)
SELECTED = dict(IOREG='1', OUTPUT_NEG='1', OLAT='1', IFN='1')


def raw_overrides(block):
    """Use the existing named-override parser but retain original expressions.

    Its masked values intentionally omit string literals for fixed-child seals;
    a parent adapter must preserve those literals and symbolic INSTANCE names.
    """
    names = _named_overrides(block)
    code = _masked_rtl(block)
    out, cursor = {}, 0
    for name in names:
        hit = re.search(r'\.' + re.escape(name) + r'\s*\(', code[cursor:])
        start = cursor + hit.end()
        end, depth = start, 1
        while depth:
            depth += (code[end] == '(') - (code[end] == ')')
            end += 1
        out[name] = block[start:end-1].strip()
        cursor = end
    return out


def adapt(text, contracts):
    digest = hashlib.sha256(text.encode()).hexdigest()
    edits, rows, seen = [], [], set()
    profiles = set()
    for contract in contracts:
        if contract['source_sha256'] != digest:
            raise ValueError('ROMQ parent source hash differs from captured contract')
        instance = contract['native_instance']
        if instance in seen:
            raise ValueError('duplicate ROMQ parent instance: ' + instance)
        seen.add(instance)
        if contract['original_master'] != MASTER or contract['selected_shell'] != SHELL:
            raise ValueError('unsupported ROMQ parent master/shell')
        hits = _instance_type_spans(text, MASTER, instance)
        if len(hits) != 1:
            raise ValueError(f'{instance}: expected one source call, found {len(hits)}')
        a, b, end = hits[0]
        old = raw_overrides(text[b:end])
        if old != contract['original_params']:
            raise ValueError(instance + ': overrides differ from captured contract')
        if not old.get('INSTANCE'):
            raise ValueError(instance + ': explicit INSTANCE expression required')
        if _literal_integer(old.get('NB', '')) != 2:
            raise ValueError(instance + ': NB must be explicitly sealed to 2')
        for name, value in old.items():
            if name == 'INSTANCE':
                if not value:
                    raise ValueError(instance + ': empty INSTANCE expression')
                continue
            if name == 'OLAT' and _literal_integer(value) in (0, 1):
                continue  # The accepted OLAT1 phase event is explicit below.
            if name == 'CGR':
                if _literal_integer(value) not in ALLOWED_CGR:
                    raise ValueError(instance + ': unsupported parameter CGR=' + value)
                continue  # the sealed child value is the contract's selected CGR below
            if name not in FIXED or _literal_integer(value) != FIXED[name]:
                raise ValueError(instance + ': unsupported parameter ' + name + '=' + value)
        new = {k:v for k,v in old.items() if k != 'NB'}
        new.update(SELECTED)
        if 'CGR' in contract['selected_params']:
            sel = contract['selected_params']['CGR']
            if _literal_integer(sel) not in ALLOWED_CGR:
                raise ValueError(instance + ': selected CGR=' + sel + ' is neither the recipe value nor the legacy seal')
            new['CGR'] = sel
        stages = (contract.get('input_stages', 1), contract.get('output_stages', 1))
        pair = contract.get('input_pair', 0)
        profile = stages + (pair,)
        if profile not in ((1, 1, 0), (3, 2, 0), (3, 2, 1), (4, 2, 1)) or any(type(x) is not int for x in profile):
            raise ValueError(instance + ': unsupported capture-stage profile')
        profiles.add(profile)
        if 'input_stages' in contract or 'output_stages' in contract:
            new.update(INPUT_STAGES=str(stages[0]), OUTPUT_STAGES=str(stages[1]))
        if 'input_pair' in contract:
            new['INPUT_PAIR'] = str(pair)
        if new != contract['selected_params']:
            raise ValueError(instance + ': selected form differs from explicit contract')
        block = SHELL + ' #(' + ', '.join('.' + k + '(' + v + ')' for k,v in new.items()) + ') '
        edits.append((a, end, block))
        rows.append(dict(instance=instance, input_params=old, selected_params=new,
                         retained_instance_expression=old.get('INSTANCE'), removed_sealed_param=dict(NB=2)))
    if len(profiles) != 1:
        raise ValueError("one explicit ROMQ capture-stage profile required per parent type")
    input_stages, output_stages, input_pair = next(iter(profiles))
    for a, end, block in sorted(edits, reverse=True):
        text = text[:a] + block + text[end:]
    return text, dict(schema='opentallas.romq_parent_adapter.v1', source_sha256=digest,
                      output_sha256=hashlib.sha256(text.encode()).hexdigest(), instances=rows,
                      input_stages=input_stages, output_stages=output_stages, input_pair=input_pair,
                      physical_FF_per_ROMQ=605*(input_stages+input_pair)+131*output_stages,
                      added_interface_cycles=input_stages + output_stages,
                      added_child_reset_edges=input_stages,
                      physical_status='PREPARATION_ONLY',
                      pending=['qualified exact child exports under accepted view/tag policy', 'COL parent capture/clock/buffer row budget',
                               'actual full-cone pin/capture/consumer reach', 'PG/clock endpoint handoff',
                               'explicit compiler/plan cycle adoption', 'native final signoff and routed EQ'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rtl', required=True, type=Path)
    p.add_argument('--contracts', required=True, type=Path)
    p.add_argument('--type', required=True)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--receipt', required=True, type=Path)
    a = p.parse_args()
    if a.rtl.resolve() == a.out.resolve():
        p.error('output must be a new source path; input is immutable')
    contracts = [r for r in json.loads(a.contracts.read_text())['rows'] if r['type'] == a.type]
    if not contracts:
        p.error('no captured contracts for selected type')
    text, receipt = adapt(a.rtl.read_text(), contracts)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(text)
    a.receipt.write_text(json.dumps(receipt, indent=1) + '\n')


if __name__ == '__main__':
    main()
