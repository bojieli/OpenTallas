"""S81-LEAF-CYC 11-11 (COORD class fix): vp_local gate/intake accept the measured station forms, one proof per form."""
import copy
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / 'vp_local_1026')]
from layer_prog import vp_local_intake as VI  # noqa: E402
from vp_local_1026.forms import DEFAULT, FORMS, effective, form_of  # noqa: E402

QUAD_OVR = dict(CS_HI_D=1, CS_HI_GS=1, CS_HO_D=1, CS_HO_GS=1)


def test_forms():
    assert FORMS['default'] == DEFAULT == VI.PARAMS
    assert form_of(effective({})) == 'default'
    assert form_of(effective(QUAD_OVR)) == 'quad'
    assert form_of(effective(dict(CS_HI_D=1, CS_HO_D=1))) == 'kv_lane'
    assert form_of(effective(dict(CS_HI_D=2, CS_HI_GS=2, CS_HO_D=2, CS_HO_GS=2))) == 'quad2'
    assert form_of(effective(dict(CS_HI_D=2, CS_HI_GS=1, CS_HO_D=2, CS_HO_GS=2))) is None   # mixed tree not measured
    assert form_of(effective(dict(CS_HI_D=1))) is None          # half a form is not measured
    assert form_of(effective(dict(ML=6))) is None
    with pytest.raises(ValueError):
        effective(dict(SR=1))                                    # an override the gate never measured


@pytest.fixture
def world(tmp_path, monkeypatch):
    root = tmp_path / 'src'
    for p in (VI.VP, VI.MEM):
        (root / p).parent.mkdir(parents=True, exist_ok=True)
        (root / p).write_text('module m; endmodule\n')
    sha = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in (VI.VP, VI.MEM)}
    man = root / 'manifest.json'
    man.write_text('{}')
    ss = types.ModuleType('layer_prog.slice_source')
    ss.manifest_selection = lambda r, m: (man, {'defines': []}, None, None)
    be = types.ModuleType('bind_elab')
    be.pick = lambda files, master, prefer: (str(root / (VI.VP if master == 'ot_s81sl_vp' else VI.MEM)), False)
    monkeypatch.setitem(sys.modules, 'layer_prog.slice_source', ss)
    monkeypatch.setitem(sys.modules, 'bind_elab', be)

    def proof(form, commit=20):
        return dict(schema='opentallas.s81.vp_local_gate.v1', status='PASS', form=form, parameters=FORMS[form],
                    clock_period_ps=833, source_sha256=sha, source_asbuilt_sha256='a', source_top_sha256='t',
                    source_event='e', checks=dict(positive=dict(passed=True, exit_code=0),
                                                  negative_payload=dict(passed=True, exit_code=1)),
                    commit_edges=[commit] * 49, output_edges=dict(HLOAD=7, GAIN=9, RDOUT=3))
    leaves, units = [], {}
    for s in range(16):
        for k in range(5):
            vp = f'u_s{s}.u_lf{k}.u_vp'
            leaves.append(dict(slice=s, leaf=k, vp=vp, status='PASS', target5_transport_edges=4,
                               command_transport_edges=5,
                               fields={f: dict(age_edges=4) for f in ('sw_v', 'sw_a', 'sw_m', 'sw_d')}
                               | {f: dict(age_edges=5) for f in ('c_v', 'c_d')}))
            units[vp] = dict(master='ot_s81sl_vp', params={} if s == 3 else dict(QUAD_OVR))
    tr = dict(verdict='PASS_BOUND_TRANSPORT', die_sha256='t', source_asbuilt_sha256='a', leaves=leaves)
    inv = dict(source_top_sha256='t', source_asbuilt_sha256='a', units=units)
    return dict(root=root, man=man, tr=tr, inv=inv, proof=proof)


def run(w, proofs, inv=None):
    return VI.attach(w['tr'], inv or w['inv'], proofs, w['root'], w['man'])


def test_default_only_still_passes(world):
    inv = copy.deepcopy(world['inv'])
    for u in inv['units'].values():
        u['params'] = {}
    r = run(world, world['proof']('default'), inv)          # existing single-proof callers unchanged
    assert r['vp_local_intake']['effective_params'] == DEFAULT and r['vp_local_intake']['forms'] == {'default': 80}


def test_quad_needs_its_own_proof(world):
    with pytest.raises(ValueError, match='no qualified proof of their form'):
        run(world, world['proof']('default'))               # the old gate alone cannot vouch for quad vps


def test_mixed_forms_each_get_their_proof(world):
    r = run(world, [world['proof']('default', 20), world['proof']('quad', 22)])
    assert r['vp_local_intake']['forms'] == {'default': 5, 'quad': 75}
    by = {x['vp']: x for x in r['leaves']}
    assert by['u_s3.u_lf0.u_vp']['local_vp_form'] == 'default' and by['u_s3.u_lf0.u_vp']['local_vp_store_commit_edges'] == 20
    assert by['u_s0.u_lf0.u_vp']['local_vp_form'] == 'quad' and by['u_s0.u_lf0.u_vp']['local_vp_store_commit_edges'] == 22


def test_controls(world):
    P = world['proof']
    with pytest.raises(ValueError, match='two proofs'):
        run(world, [P('quad'), P('quad'), P('default')])
    bad = P('quad'); bad['parameters'] = dict(bad['parameters'], CS_HI_GS=0, CS_HO_GS=1)
    with pytest.raises(ValueError, match='measured form'):
        run(world, [P('default'), bad])
    lab = P('quad'); lab['form'] = 'default'
    with pytest.raises(ValueError, match='label'):
        run(world, [lab])
    inv = copy.deepcopy(world['inv']); inv['units']['u_s0.u_lf0.u_vp']['params'] = dict(ML=6)
    with pytest.raises(ValueError):
        run(world, [P('default'), P('quad')], inv)
    ch = P('quad'); ch['source_sha256'] = dict(ch['source_sha256'], **{VI.VP: '0' * 64})
    with pytest.raises(ValueError, match='different sources|source changed'):
        run(world, [P('default'), ch])


def test_gate_form_cli(tmp_path):
    """gate.py --form: the audit accepts measured forms only and the tb gets the form as -G overrides (no build)."""
    g = (HERE.parent / 'vp_local_1026' / 'gate.py').read_text()
    assert "add_argument('--form',choices=sorted(FORMS),default='default')" in g
    assert "-G{k}={x}' for k,x in required.items()" in g
    tb = (HERE.parent / 'vp_local_1026' / 'tb_vp_local.sv').read_text()
    assert '.CS_HI_D(CS_HI_D),.CS_HI_GS(CS_HI_GS),.CS_HO_D(CS_HO_D),.CS_HO_GS(CS_HO_GS)' in tb
    audit = dict(units={f'u{i}': FORMS['quad' if i else 'default'] for i in range(80)},
                 source_top_sha256='x', source_asbuilt_sha256='y')
    (tmp_path / 'a.json').write_text(json.dumps(audit))
    (tmp_path / 'e.json').write_text(json.dumps(dict(die_sha256='other', writes=[])))
    r = subprocess.run([sys.executable, '-I', str(HERE.parent / 'vp_local_1026' / 'gate.py'), '--entry-rows',
                        str(tmp_path / 'e.json'), '--params', str(tmp_path / 'a.json'), '--out', str(tmp_path / 'o'),
                        '--form', 'kv_lane'], capture_output=True, text=True)
    assert r.returncode != 0 and 'AssertionError' in r.stderr  # kv_lane is not in this audit
    r = subprocess.run([sys.executable, '-I', str(HERE.parent / 'vp_local_1026' / 'gate.py'), '--entry-rows',
                        str(tmp_path / 'e.json'), '--params', str(tmp_path / 'a.json'), '--out', str(tmp_path / 'o2'),
                        '--form', 'quad'], capture_output=True, text=True)
    assert r.returncode != 0 and "die_sha256" in r.stderr     # passes the form audit, stops at the image check


# S81-D8E-LAT 11-18: the XR write-port stage (s81_vp_xr_overlay, LF_VP_XR on every D8e leaf) is its own measured form
def test_xr_forms():
    assert form_of(effective(dict(QUAD_OVR, XR=1))) == 'quad_xr'
    assert form_of(effective(dict(CS_HI_D=1, CS_HO_D=1, XR=1))) == 'kv_lane_xr'
    assert form_of(effective(dict(QUAD_OVR, XR=0))) == 'quad'        # overlay present, XR off = the plain form
    assert effective(dict(XR=0)) == DEFAULT and form_of(dict(DEFAULT, XR=0)) == 'default'
    assert FORMS['quad_xr'] == dict(FORMS['quad'], XR=1)


def test_xr_vp_needs_xr_proof(world):
    inv = copy.deepcopy(world['inv'])
    for u in inv['units'].values():
        u['params'] = dict(u['params'], XR=1)
    with pytest.raises(ValueError, match='no qualified proof of their form'):
        run(world, [world['proof']('default'), world['proof']('quad')], inv)     # XR=0 proofs cannot vouch for XR vps
    r = run(world, [world['proof']('default_xr', 21), world['proof']('quad_xr', 23)], inv)
    assert r['vp_local_intake']['forms'] == {'default_xr': 5, 'quad_xr': 75}
    by = {x['vp']: x for x in r['leaves']}
    assert by['u_s0.u_lf0.u_vp']['local_vp_store_commit_edges'] == 23


def test_gate_xr_tb_patch(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('vp_local_gate', HERE.parent / 'vp_local_1026' / 'gate.py')
    G = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(G)
    assert G.tb_for(FORMS['quad'], tmp_path).name == 'tb_vp_local.sv' and not (tmp_path / 'tb_vp_local.sv').exists()
    t = G.tb_for(FORMS['quad_xr'], tmp_path).read_text()
    assert 'HQX = 0, XR = 0);' in t and '.HQX(HQX),.XR(XR)) u_vp(' in t


def test_gate_xr_form_refuses_source_without_overlay(tmp_path):
    audit = dict(units={f'u{i}': FORMS['quad_xr'] for i in range(80)}, source_top_sha256='x', source_asbuilt_sha256='y')
    (tmp_path / 'a.json').write_text(json.dumps(audit))
    rows = [dict(sid=0, leaf=0, row=r, data128='0' * 32) for r in list(range(32)) + list(range(64, 80)) + [1008]]
    (tmp_path / 'e.json').write_text(json.dumps(dict(die_sha256='x', fixture_meta_sha256='f', writes=rows)))
    src = tmp_path / 'src' / 'rtl/dsrom_sys/s81_dv/slice'
    src.mkdir(parents=True)
    (src / 'ot_s81sl_vp.sv').write_text('module ot_s81sl_vp; endmodule\n')
    r = subprocess.run([sys.executable, '-I', str(HERE.parent / 'vp_local_1026' / 'gate.py'), '--entry-rows',
                        str(tmp_path / 'e.json'), '--params', str(tmp_path / 'a.json'), '--out', str(tmp_path / 'o'),
                        '--form', 'quad_xr', '--source-root', str(tmp_path / 'src')], capture_output=True, text=True)
    assert r.returncode != 0 and 'S81-STRIP-XR' in r.stderr
