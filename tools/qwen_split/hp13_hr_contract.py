"""Reconcile exact fixed-native HR source captures with the actual GEN lane."""
import hashlib
import json
from pathlib import Path
from qwen_split import lane_groups as LG


def compiled_params(root, master):
    from qwen_split.headprep_corepub_source import CONTRACTS, select
    variants = [v for v,c in CONTRACTS.items() if c['master'] == master]
    if len(variants) != 1: raise ValueError('unknown fixed native source: ' + master)
    select(root, variants[0])
    p = Path(root) / 'results/arch/qw_headprep_1021/rrloc_projection/native_frontend/input_source_inventory.json'
    if hashlib.sha256(p.read_bytes()).hexdigest() != '0628894976428558b8d60901f44d4a739113b1598740c867dd0d3db51051e8c3':
        raise ValueError('fixed native construction parameter inventory differs')
    return json.loads(p.read_text())['params']


def reconcile(root, master, hr_rows):
    root=Path(root)
    rows=json.loads((root/'results/arch/hp13_corepub39_1021/HR_SOURCE_CONTRACT.json').read_text())
    contracts=[r for r in rows if r['master']==master]
    if len(contracts)!=1:raise ValueError('HP13 fixed native has no exact HR source contract: '+master)
    c=contracts[0]
    for path,digest in ((c['rtl'],c['rtl_sha256']),
                        (c['compiled_construction_receipt'],c['compiled_construction_receipt_sha256'])):
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('HP13 HR source/construction identity differs: '+path)
    arm=c['ARM72'];bits=arm['bit_rows']
    if c['clock_port']!='ck_hr' or arm['source_to_HR_output_edges']!=1 or len(bits)!=72:
        raise ValueError('HP13 actual ARM source relation differs')
    for b in bits:
        o=b['output_register']
        if 'source_registers' in b:
            # QDIE5-HP13 10-22 (QW-SEGCAL xpf_hr = xpf_g[0] ? xpf_g : xpf): the HR capture D is a combinational cone of
            # ck_hr scheduler register Qs (regen_hr_contract.py proves it on the netlist) -- still ONE register edge
            srcs=b['source_registers']
            if not srcs or any(s['C']!=o['C'] for s in srcs):
                raise ValueError('HP13 actual ARM capture relation differs')
        else:
            s=b['source_register']
            if o['D']!=s['Q'] or o['C']!=s['C']:
                raise ValueError('HP13 actual ARM capture relation differs')
    if not hr_rows:raise ValueError('HP13 actual HR GEN route is missing')
    actual={bid:LG.lane_cycles(row) for bid,row in hr_rows}
    if any(v is None for v in actual.values()) or len(set(actual.values()))!=1:
        raise ValueError('HP13 actual HR route ages are unresolved or disagree: '+str(actual))
    age=next(iter(actual.values()));fixed=c['compiled_XPF_TRANSPORT_EDGES']
    params = compiled_params(root, master)
    if params['XPF_TRANSPORT_EDGES'] != fixed:
        raise ValueError('fixed native source construction and HR contract disagree')
    if arm['source_to_HR_output_edges']+age!=fixed:
        raise ValueError(f'HP13 fixed XPF {fixed} differs from source ARM capture 1 + actual GEN HR lane {age}; regenerate source for actual route')
    return fixed,dict(XPF_TRANSPORT_EDGES=fixed,hr_pin_register=arm['source_to_HR_output_edges'],
        lane_cycles=age,actual_lanes=actual,source_master=master,source_sha256=c['rtl_sha256'],
        clock_port='ck_hr',law='source-proven ARM capture + actual GEN lane = fixed native construction',
        compiled_params=params,parameter_overrides=False,physical_qualification_eligible=False)
