"""Default-off bridge for the reviewed four-stage HBM SPB0 transport.

Mechanism/assets originate in reviewed candidate e64c6bba8. Production callers
must supply their actual selected source graph and delivered clock/reset contract.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import re
import shutil
from pathlib import Path

ASSETS = Path(__file__).with_name('hbm_spb0_assets')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repo_file(base, name):
    if not isinstance(name, str) or Path(name).is_absolute():
        raise ValueError('SPB native inputs must be repository-relative files')
    path = (Path(base) / name).resolve()
    path.relative_to(Path(base).resolve())
    if not path.is_file():
        raise ValueError(f'missing SPB native input {name}')
    return path


def materialize(binder, typ, bound):
    cfg = binder.ab.get('hbm_spb0_native')
    if cfg is None:
        return []
    allowed = {'q_spb0', 'q_spb0__physical_v1'}
    if (not isinstance(cfg, dict) or set(cfg) != {'types', 'graph', 'contract'} or
            not isinstance(cfg['types'], list) or not cfg['types'] or
            not all(isinstance(t, str) for t in cfg['types']) or
            len(set(cfg['types'])) != len(cfg['types']) or not set(cfg['types']) <= allowed):
        raise ValueError('HBM SPB native requires exact reviewed SPB types/graph/contract opt-in')
    if typ not in cfg['types']:
        return []
    graph = repo_file(binder.base, cfg['graph'])
    contract = repo_file(binder.base, cfg['contract'])
    c = json.loads(contract.read_text())
    if (c.get('schema') != 'opentallas.hbm.spb0_contract.v1' or
            (c.get('lk_instance'), c.get('ep_instance'), c.get('lk_module'), c.get('ep_module')) !=
            ('u_lk_S0', 'u_ep_S0', 'ot_pdie_serdes', 'hfd_ep_static')):
        raise ValueError('SPB native requires exact reviewed endpoint modules/instances')
    placement = (contract.parent / c['placement_file']).resolve()
    placement.relative_to(Path(binder.base).resolve())
    if not placement.is_file():
        raise ValueError('missing source-owned SPB bank placement')
    plan = getattr(binder, 'source_plan', None)
    if plan is None or digest(plan) != c.get('plan_sha256'):
        raise ValueError('SPB native contract does not match actual source plan file')
    expected_parts = sorted(p for p, d in binder.parts.items() if d['type'] in cfg['types'])
    if sorted(c['partitions']) != expected_parts:
        raise ValueError('SPB native graph contract must cover exact physical replicas')
    text = Path(bound).read_text()
    for inst, master in ((c['lk_instance'], c['lk_module']), (c['ep_instance'], c['ep_module'])):
        # Check actual bound master, not only the graph's declared module.
        if not re.search(r'\b' + re.escape(master) + r'\s*(?:#\(.*?\)\s*)?' + re.escape(inst) + r'\s*\(', text, re.S):
            raise ValueError(f'SPB actual bound instance/master mismatch: {inst}/{master}')
    spec = importlib.util.spec_from_file_location('spb_native_mechanism', ASSETS / 'spb0_native.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    out = Path(bound).parent / 'hbm_spb0_native' / typ
    with contextlib.redirect_stdout(io.StringIO()):
        adapter.run(bound, graph, contract, out)
    transformed = out / Path(bound).name
    files = [transformed, out / 'ot_hbm_spb0_regs.sv', out / 'placement.json',
             out / 'spb_native_sites.tcl', out / 'spb_native_banks.tcl', out / 'receipt.json']
    identity = {f.name: digest(f) for f in files}
    (out / 'materialization.json').write_text(json.dumps(identity, indent=1) + '\n')
    shutil.copyfile(transformed, bound)
    return [out / 'ot_hbm_spb0_regs.sv']


def kit_geometry(out, typ, text, kit):
    if not re.search(r'\bot_hbm_spb0_regs\b', text):
        return None
    source = Path(out) / 'rtl' / 'hbm_spb0_native' / typ
    if not source.is_dir():
        source = Path(out) / 'hbm_spb0_native' / typ
    identity = json.loads((source / 'materialization.json').read_text())
    for name, sha in identity.items():
        if Path(name).name != name or digest(source / name) != sha:
            raise ValueError('SPB native materialization input changed')
    transformed = [name for name in identity if name.endswith('.sv') and name != 'ot_hbm_spb0_regs.sv']
    if len(transformed) != 1 or hashlib.sha256(text.encode()).hexdigest() != identity[transformed[0]]:
        raise ValueError('SPB native bound RTL differs from materialization')
    receipt = json.loads((source / 'receipt.json').read_text())
    expected = [dict(module='ot_hbm_spb0_regs',instance='u_hbm_spb0_rx',W=514,N=4,CW=2),
                dict(module='ot_hbm_spb0_regs',instance='u_hbm_spb0_tx',W=512,N=4,CW=0)]
    if receipt['station_modules'] != expected or receipt['actual_new_ff_per_partition'] != 4104:
        raise ValueError('SPB native module/parameter/count mismatch')
    # Single self-contained sidecar survives gen_phys' existing istations copy.
    target = Path(kit)
    prior = (target / 'istations.tcl').read_text() if (target / 'istations.tcl').is_file() else ''
    (target / 'istations.tcl').write_text(prior + '\n' + (source / 'spb_native_sites.tcl').read_text() + '\n' +
                                        (source / 'spb_native_banks.tcl').read_text())
    for name in ('receipt.json', 'placement.json', 'materialization.json'):
        shutil.copyfile(source / name, target / ('spb_native_' + name))
    return dict(rtl=str(source / 'ot_hbm_spb0_regs.sv'), stations=8, flops=4104, tcl='istations.tcl', receipt='spb_native_receipt.json',
                rtl_cycles_changed={'rx_st':4,'tx':4}, model_cycles_changed={'rx_st':2,'tx':0})
