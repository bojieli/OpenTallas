"""Typed native controls are skipped; declared data remains a real boundary gate."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff
from test_face_guard import NET_OK


def fixture(tmp_path):
    net = NET_OK.replace('top(clk, a, o)', 'top(clk, rst, unused_clk, a, o)').replace(
        'input clk;', 'input clk; input rst; input unused_clk;')
    (tmp_path / 'synth.v').write_text(net)
    (tmp_path / 'core.json').write_text(json.dumps({'boundary_role': {
        'clk': 'clk', 'rst': 'reset', 'unused_clk': 'clk_unused', 'a': 'in', 'o': 'out'}}))
    ctx = dict(schema='opentallas.core_boundary_guard_context.v1', source_core_json='core.json',
               clock_ports=['clk'], unused_clock_ports=['unused_clk'], reset_ports=['rst'], data_pin_exemptions=[])
    (tmp_path / 'boundary_guard_context.json').write_text(json.dumps(ctx))
    return dict(kit=str(tmp_path), synth=str(tmp_path / 'synth.v')), ctx


def test_real_native_control_roles(tmp_path):
    disc, ctx = fixture(tmp_path)
    r = signoff.run_face_guard(disc)
    assert r['verdict'] == 'PASS' and r['checked'] == 4, r
    # Missing metadata must still expose the unused native ports.
    (tmp_path / 'boundary_guard_context.json').unlink()
    assert signoff.run_face_guard(disc)['verdict'] == 'FAIL'


def test_dropped_data_is_still_required(tmp_path):
    disc, ctx = fixture(tmp_path)
    p = Path(disc['synth'])
    p.write_text(p.read_text().replace('.D(a[1])', '.D(q[0])'))
    r = signoff.run_face_guard(disc)
    assert r['verdict'] == 'FAIL' and r['fail_counts']['dropped'], r


def test_data_exemption_and_role_mutants_rejected(tmp_path):
    disc, ctx = fixture(tmp_path)
    p = tmp_path / 'boundary_guard_context.json'
    ctx['data_pin_exemptions'] = ['a']
    p.write_text(json.dumps(ctx))
    assert signoff.run_face_guard(disc)['fail_counts'] == {'context': 1}
    ctx['data_pin_exemptions'] = []
    ctx['reset_ports'].append('a')  # a is typed as real input data, not reset.
    p.write_text(json.dumps(ctx))
    assert signoff.run_face_guard(disc)['fail_counts'] == {'context': 1}


def test_uniform_guard_honors_exact_one_station_contract(tmp_path):
    from test_face_guard import NET_FT1
    (tmp_path / 'synth.v').write_text(NET_FT1)
    disc = dict(kit=str(tmp_path), synth=str(tmp_path / 'synth.v'))
    assert signoff.run_face_guard(disc)['verdict'] == 'FAIL'
    table = tmp_path / 'ft_stations.txt'
    table.write_text('ft0 1 S W\nft1 1 S W\n')
    r = signoff.run_face_guard(disc)
    assert r['verdict'] == 'PASS' and r['one_station_ft_slots'] == ['ft0', 'ft1'], r
    table.write_text('ft0 1 S W\nft1 2 S W\n')
    assert signoff.run_face_guard(disc)['fail_counts'] == {'merged': 2}
