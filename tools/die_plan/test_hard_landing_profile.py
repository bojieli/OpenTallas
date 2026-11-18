"""Portable landing receipts use measured profile gates, with identities intact."""
import json

import pytest

import hard_landing as H
from test_face_guard import _mux_mod, _mux_slots4, _mux_tc


def receipt():
    return dict(verdict='LOCAL_PASS_NEEDS_PARENT', local_verdict='SIGNED',
                checks=dict(drc=dict(count=0), setup_tt=dict(wns_ps=149),
                            hold_ff=dict(wns_ps=-1.34, verdict='PASS', port_only_needs_parent=True)),
                corners=dict(ff=dict(done=True, errors=[], rc=0,
                                    std_min_start=dict(err=0, trunc=0, core_n=0, core_wns=0))))


def evidence(tmp_path, signoff):
    d = tmp_path / 'macros' / 'landing' / 'top'
    d.mkdir(parents=True)
    net = _mux_mod(_mux_tc() + _mux_slots4()).replace('module top(fclk, d);',
                                                    'module top(clk, fclk, d);\n input clk;')
    payloads = {'netlist.v': net, 'land_slots.json': json.dumps(dict(buses=dict(d=dict(D=4, form='hold_mux')))),
                'signoff.json': json.dumps(signoff), 'face_guard_source.py': '# frozen child tool\n',
                'face_guard.json': json.dumps(dict(verdict='PASS', top='top', netlist='captured_child.v')),
                'top.lef': 'exact LEF', 'top_tt.lib': 'exact LIB'}
    for name, text in payloads.items():
        (d / name).write_text(text)
    for name in ('top.lef', 'top_tt.lib'):
        (d.parents[1] / name).write_bytes((d / name).read_bytes())
    signoff['face_guard'] = dict(verdict='PASS', top='top', netlist='captured_child.v')
    (d / 'signoff.json').write_text(json.dumps(signoff))
    provenance = dict(kit=dict(module='top', face_guard_sha256=H.digest(d / 'face_guard_source.py')),
                      export=dict(signoff_sha256=H.digest(d / 'signoff.json'),
                                  files_sha256={n: H.digest(d / n) for n in ('top.lef', 'top_tt.lib')}))
    (d / 'provenance.json').write_text(json.dumps(provenance))
    manifest = dict(schema='hard_landing/1', master='top', D=4, width=1, base=H.PLAIN_BASE,
                    lef='top.lef', lib='top_tt.lib', netlist_source='captured_child.v',
                    sha256={n: H.digest(d / n) for n in [*payloads, 'provenance.json']})
    (d / 'manifest.json').write_text(json.dumps(manifest))
    return d


def test_complete_port_only_receipt_reproves_actual_face_without_rewriting(tmp_path, monkeypatch):
    monkeypatch.setenv('OT_SIGNOFF_PROFILE', 'minimal')
    d = evidence(tmp_path, receipt())
    original = {p.name: p.read_bytes() for p in d.iterdir()}
    manifest, proof = H.prove(d)
    assert manifest['width'] == 1 and proof['verdict'] == 'PASS' and proof['land_mux_bits'] == 1
    assert {p.name: p.read_bytes() for p in d.iterdir()} == original
    assert json.loads((d / 'signoff.json').read_text())['verdict'] == 'LOCAL_PASS_NEEDS_PARENT'


@pytest.mark.parametrize('mutation', ['missing_census', 'negative_internal', 'truncated', 'not_done', 'drc', 'setup', 'label_only'])
def test_profile_failures_never_become_signed_from_the_old_label(tmp_path, monkeypatch, mutation):
    monkeypatch.setenv('OT_SIGNOFF_PROFILE', 'minimal')
    s = receipt()
    ff = s['corners']['ff']
    if mutation == 'missing_census': ff['std_min_start'] = {}
    if mutation == 'negative_internal': ff['std_min_start'].update(core_n=1, core_wns=-0.01)
    if mutation == 'truncated': ff['std_min_start']['trunc'] = 1
    if mutation == 'not_done': ff['done'] = False
    if mutation == 'drc': s['checks']['drc']['count'] = 1
    if mutation == 'setup': s['checks']['setup_tt']['wns_ps'] = -43
    if mutation == 'label_only': s = dict(verdict='SIGNED')
    with pytest.raises(ValueError, match='profile-qualified'):
        H.prove(evidence(tmp_path, s))


@pytest.mark.parametrize('mutation', ['signoff', 'netlist', 'selected_view'])
def test_hash_and_parent_view_guards_still_reject_tamper(tmp_path, monkeypatch, mutation):
    monkeypatch.setenv('OT_SIGNOFF_PROFILE', 'minimal')
    d = evidence(tmp_path, receipt())
    p = {'signoff': d / 'signoff.json', 'netlist': d / 'netlist.v',
         'selected_view': d.parents[1] / 'top.lef'}[mutation]
    p.write_text(p.read_text() + '\nchanged')
    with pytest.raises(ValueError, match='hash mismatch|differs from the proved'):
        H.prove(d)


@pytest.mark.parametrize('mutation', ['face', 'frozen_tool', 'exported_receipt', 'netlist_source'])
def test_rehashed_payload_cannot_bypass_face_or_export_identity(tmp_path, monkeypatch, mutation):
    monkeypatch.setenv('OT_SIGNOFF_PROFILE', 'minimal')
    d = evidence(tmp_path, receipt())
    manifest = json.loads((d / 'manifest.json').read_text())
    if mutation == 'face':
        p = d / 'face_guard.json'
        face = json.loads(p.read_text())
        face['verdict'] = 'FAIL'
        p.write_text(json.dumps(face))
    elif mutation == 'frozen_tool':
        (d / 'face_guard_source.py').write_text('# different tool\n')
    elif mutation == 'exported_receipt':
        (d / 'signoff.json').write_text((d / 'signoff.json').read_text() + '\n')
    else:
        manifest['netlist_source'] = 'different_child.v'
    manifest['sha256'] = {name: H.digest(d / name) for name in manifest['sha256']}
    (d / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='face evidence|frozen child tool|exported view signoff|face-proof input'):
        H.prove(d)


def test_legacy_does_not_accept_local_pass_label(tmp_path, monkeypatch):
    monkeypatch.setenv('OT_SIGNOFF_PROFILE', 'legacy')
    with pytest.raises(ValueError, match='profile-qualified'):
        H.prove(evidence(tmp_path, receipt()))
