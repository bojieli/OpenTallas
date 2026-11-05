"""Mean-versus-extremum controls and release qualification of core contracts."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pytest
import core_clock_contract as CC
import early_core_taps as E


def core(tmp_path):
    lib = tmp_path/'node_tt.lib'
    lib.write_text('''library(node) { time_unit : "1ps"; cell(node) { pin(clk) {
      direction : input;
      clock : true;
      timing() { timing_type : max_clock_tree_path;
        cell_rise(scalar) { values("267.63058"); } cell_fall(scalar) { values("280"); }
      }
    } } }''')
    return dict(inst='u_node', module='node', lib=str(lib))


def signed():
    return dict(verdict='SIGNED', corners={c:dict(done=True,design='node',parasitics='spef',clock_ports=['clk'],
                   insertion_pinflops=dict(n=2058,mean=m,min=m-15,max=m+17))
                for c,m in [('tt',245.9),('ff',199.6)]})


def test_selected_mean_is_not_etm_max(tmp_path):
    c=core(tmp_path)
    (tmp_path/'signoff.json').write_text(json.dumps(signed()))
    v=CC.load(c)['clk']
    assert v['signed']
    assert v['corners']['tt']['mean_ps']==245.9
    assert v['corners']['ff']['mean_ps']==199.6
    assert v['corners']['tt']['mean_ps'] != 267.63058
    # Release early-tap policy must not use max267.63 to add a17.63ps tap.
    # Geometry stub exists only to prove this no-tap decision on a real reader.
    (tmp_path/'node.lef').write_text('MACRO node\n SIZE 10 BY 10 ;\nEND node\n')
    c.update(lef=str(tmp_path/'node.lef'),origin_um=[0,0],outline_um=[10,10])
    assert E.add_from_means(dict(hard_cores=[c],clock={}))==[]


def test_local_pass_needs_parent_counts_signed(tmp_path):
    """OWNER 11-03: LOCAL_PASS_NEEDS_PARENT counts as signed; other verdicts still refuse."""
    c=core(tmp_path)
    rec=signed(); rec['verdict']='LOCAL_PASS_NEEDS_PARENT'
    (tmp_path/'signoff.json').write_text(json.dumps(rec))
    v=CC.load(c)['clk']
    assert v['signed'] and v['corners']['tt']['mean_ps']==245.9
    rec['verdict']='FAIL'
    (tmp_path/'signoff.json').write_text(json.dumps(rec))
    with pytest.raises(CC.ContractError, match='not SIGNED'):
        CC.load(c)


def test_signed_claim_missing_mean_fails(tmp_path):
    c=core(tmp_path);r=signed();del r['corners']['ff']['insertion_pinflops']['mean']
    (tmp_path/'signoff.json').write_text(json.dumps(r))
    with pytest.raises(CC.ContractError,match='mean'):CC.load(c)


def test_historical_measurement_is_diagnostic_only(tmp_path):
    c=core(tmp_path)
    (tmp_path/'insertion.json').write_text(json.dumps(dict(raw_source=True,parasitics='spef',lib_clock_pin='clk',
        tt=dict(boundary=dict(n=2058,mean=245.9,max=263.4),errors=[]),
        ff=dict(boundary=dict(n=2058,mean=199.6,max=216.9),errors=[]))))
    assert CC.load(c,require_signed=False)['clk']['corners']['tt']['mean_ps']==245.9
    with pytest.raises(CC.ContractError,match='SIGNED'):CC.load(c)


def test_explicit_parent_budget_cannot_claim_signed(tmp_path):
    c=core(tmp_path)
    b=CC.from_budget(c['lib'],dict(clk=dict(tt=250.,ff=202.5)),'A0 first-route parent budget')
    (tmp_path/'clock_contract.json').write_text(json.dumps(b))
    v=CC.load(c,require_signed=False)['clk']
    assert v['corners']['ff']['basis']=='parent_budget' and not v['signed']
    with pytest.raises(CC.ContractError,match='SIGNED'):CC.load(c)


def test_contract_view_mismatch_and_wrong_design_controls(tmp_path):
    c=core(tmp_path);r=signed()
    raw=CC.from_signoff(c['lib'],r,'test/signoff.json')
    (tmp_path/'clock_contract.json').write_text(json.dumps(raw))
    Path(c['lib']).write_text(Path(c['lib']).read_text()+'\n// other view\n')
    with pytest.raises(CC.ContractError,match='liberty'):CC.load(c)
    r['corners']['ff']['design']='other_variant'
    with pytest.raises(CC.ContractError,match='design'):CC.from_signoff(c['lib'],r,'test/signoff.json')


def test_optin_export_keeps_corner_and_source_basis(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import gen_phys as G
    c=core(tmp_path)
    (tmp_path/'signoff.json').write_text(json.dumps(signed()))
    p=SimpleNamespace(types={'tile':dict(hard_cores=[c])},clock=dict(insertion_ps=250.))
    monkeypatch.setattr(G,'core_tap_rows',lambda *_, **__: [])
    out=tmp_path/'out';out.mkdir()
    G.core_latency_files(p,'tile',out,mean_contract=True)
    assert 'u_node clk 245.9 grid' in (out/'core_latency.txt').read_text()
    assert 'u_node clk 199.6 grid' in (out/'core_latency_ff.txt').read_text()
    r=json.loads((out/'core_latency.json').read_text())['rows'][0]
    assert r['signed'] and r['corners']['ff']['basis']=='pin_register_mean'
    assert 'signoff.json' in r['signoff_source']
    (tmp_path/'signoff.json').unlink()
    with pytest.raises(CC.ContractError,match='SIGNED'):G.core_latency_files(p,'tile',out,mean_contract=True)


def test_parent_budget_trial_exports_means_release_refuses(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import gen_phys as G
    c = core(tmp_path)
    b = CC.from_budget(c['lib'], dict(clk=dict(tt=390., ff=312.)), 'parent_budget A0 centre entry')
    (tmp_path/'clock_contract.json').write_text(json.dumps(b))
    p = SimpleNamespace(types={'tile': dict(hard_cores=[c], clock=dict(core_taps='early', taps=[
        dict(name='u_node.clk', kind='core', insertion_ps=390., insertion_ff_ps=312.,
             budget_owner='parent_budget A0 centre entry')]))}, clock=dict(insertion_ps=250.))
    monkeypatch.setattr(G, 'core_tap_rows', lambda *_, **__: [('clk_c0', 'u_node', 'clk', 140., 390.)])
    out = tmp_path/'out'; out.mkdir()
    G.core_latency_files(p, 'tile', out, **G.core_mean_contract_options(p, 'tile', trial=True))
    assert 'u_node clk 390' in (out/'core_latency.txt').read_text()
    assert 'u_node clk 312' in (out/'core_latency_ff.txt').read_text()
    row = json.loads((out/'core_latency.json').read_text())['rows'][0]
    assert not row['signed'] and row['basis'] == 'parent_budget'
    # KIT-TRIAGE-1/G3 11-01: release kits take the same labelled estimate form
    assert G.core_mean_contract_options(p, 'tile', trial=False) == dict(mean_contract=True, require_signed=False)
    assert row['release_qualified'] is False
    # The export retains the selected-view and TT tap consistency controls.
    b['view_lib_sha256'] = 'wrong'
    (tmp_path/'clock_contract.json').write_text(json.dumps(b))
    with pytest.raises(CC.ContractError, match='liberty'):
        G.core_latency_files(p, 'tile', out, **G.core_mean_contract_options(p, 'tile', trial=True))


def test_mean_selector_default_signed_and_incomplete_budget_controls():
    from types import SimpleNamespace
    import gen_phys as G
    p = SimpleNamespace(types={'tile': dict(hard_cores=[dict(inst='u')])})
    assert G.core_mean_contract_options(p, 'tile', trial=True) == dict(mean_contract=False, require_signed=True)
    p.types['tile']['clock'] = dict(core_taps='early', taps=[
        dict(kind='core', insertion_ff_ps=199.6, budget_owner='SIGNED selected view')])
    assert G.core_mean_contract_options(p, 'tile', trial=False) == dict(mean_contract=True, require_signed=True)
    p.types['tile']['clock']['taps'].append(
        dict(kind='core', insertion_ff_ps=312., budget_owner='parent_budget A0'))
    assert G.core_mean_contract_options(p, 'tile', trial=True) == dict(mean_contract=True, require_signed=False)
    assert G.core_mean_contract_options(p, 'tile') == dict(mean_contract=True, require_signed=False)
    del p.types['tile']['clock']['taps'][1]['insertion_ff_ps']
    assert G.core_mean_contract_options(p, 'tile', trial=True) == dict(mean_contract=False, require_signed=True)


def test_internal_cts_keeps_signed_means_without_external_core_taps():
    from types import SimpleNamespace
    import gen_phys as G
    import schema as S
    p = SimpleNamespace(types={"tile":dict(hard_cores=[dict(inst="u")], clock=dict(
        core_taps="internal", taps=[dict(kind="core", name="u.clk", xy=[1,2],
        insertion_ps=250., insertion_ff_ps=199.6, budget_owner="SIGNED selected view")]))})
    assert S.core_taps(p,"tile") == []
    assert G.core_mean_contract_options(p,"tile") == dict(mean_contract=True,require_signed=True)
    p.types["tile"]["clock"]["taps"][0]["budget_owner"]="parent_budget trial"
    with pytest.raises(CC.ContractError,match="internal core CTS"):
        G.core_mean_contract_options(p,"tile",trial=True)


def test_internal_unsigned_core_taps_take_estimate_form():
    """DIE-KV-60/taps: internal core taps of a not-yet-SIGNED core use the other dies' estimate form (legacy rows)."""
    from types import SimpleNamespace
    import gen_phys as G
    tap = lambda owner, **k: dict(kind="core", name="u.clk", xy=[1, 2], insertion_ps=250., budget_owner=owner, **k)
    p = SimpleNamespace(types={"tile": dict(hard_cores=[dict(inst="u"), dict(inst="v")], clock=dict(
        core_taps="internal", taps=[tap("qkd_kvs_pc")]))})
    assert G.internal_core_taps_estimate(p, "tile")
    assert G.core_mean_contract_options(p, "tile") == dict(mean_contract=False, require_signed=True)
    # mixed: one signed core + one estimate core -> estimate form for the type until all cores are signed
    p.types["tile"]["clock"]["taps"] = [tap("SIGNED:v/signoff.json", insertion_ff_ps=190.), tap("kv3_pv_join")]
    assert G.core_mean_contract_options(p, "tile") == dict(mean_contract=False, require_signed=True)
    # all signed -> SIGNED mean contract (unchanged)
    p.types["tile"]["clock"]["taps"][1] = tap("SIGNED:w/signoff.json", insertion_ff_ps=191.)
    assert not G.internal_core_taps_estimate(p, "tile")
    assert G.core_mean_contract_options(p, "tile") == dict(mean_contract=True, require_signed=True)
    # parent_budget internal taps still raise (unchanged)
    p.types["tile"]["clock"]["taps"][1] = tap("parent_budget x", insertion_ff_ps=191.)
    with pytest.raises(CC.ContractError, match="internal core CTS"):
        G.core_mean_contract_options(p, "tile", trial=True)


def test_release_parent_budget_without_view_contract_uses_plan_budget(tmp_path, monkeypatch):
    """KIT-TRIAGE-1/G3 11-01 (S81 svc_*_dsdv_svc_rs__t*): the selected core view has no clock_contract/signoff/
    insertion file; a release kit takes the plan's parent_budget TT/FF means, labelled not SIGNED."""
    from types import SimpleNamespace
    import gen_phys as G
    c = core(tmp_path)
    tap = dict(name='u_node.clk', kind='core', insertion_ps=364.38, insertion_ff_ps=291.94,
               budget_owner='parent_budget pin_register_mean ROUTED NOT SIGNED')
    p = SimpleNamespace(types={'tile': dict(hard_cores=[c], clock=dict(core_taps='early', taps=[tap]))},
                        clock=dict(insertion_ps=250.))
    monkeypatch.setattr(G, 'core_tap_rows', lambda *_, **__: [('clk_c0', 'u_node', 'clk', 0., 364.38)])
    out = tmp_path/'out'; out.mkdir()
    G.core_latency_files(p, 'tile', out, **G.core_mean_contract_options(p, 'tile'))
    assert 'u_node clk 364.38' in (out/'core_latency.txt').read_text()
    assert 'u_node clk 291.94' in (out/'core_latency_ff.txt').read_text()
    row = json.loads((out/'core_latency.json').read_text())['rows'][0]
    assert row['basis'] == 'parent_budget' and row['signed'] is False and row['release_qualified'] is False
    # never SIGNED: a SIGNED-required load ignores the plan budget
    with pytest.raises(CC.ContractError, match='SIGNED'):
        CC.load(c, plan_type=p.types['tile'])
    # a measured file in the view wins over the plan budget (here: mismatch -> tap check fails loudly)
    (tmp_path/'insertion.json').write_text(json.dumps(dict(raw_source=True, parasitics='spef', lib_clock_pin='clk',
        tt=dict(boundary=dict(n=9, mean=300.0), errors=[]), ff=dict(boundary=dict(n=9, mean=240.0), errors=[]))))
    with pytest.raises(CC.ContractError, match='regenerate'):
        G.core_latency_files(p, 'tile', out, **G.core_mean_contract_options(p, 'tile'))


def test_plan_budget_partial_or_unrelated_taps_do_not_cover(tmp_path):
    c = core(tmp_path)
    t = dict(clock=dict(taps=[dict(name='u_other.clk', kind='core', insertion_ps=1., insertion_ff_ps=1.,
                                   budget_owner='parent_budget x'),
                              dict(name='u_node.clk', kind='core', insertion_ps=1., budget_owner='parent_budget y'),
                              dict(name='u_node.clk', kind='core', insertion_ps=2., insertion_ff_ps=2.,
                                   budget_owner='DIE plan z')]))
    assert CC.plan_budget(t, c, ['clk']) == {}
    with pytest.raises(CC.ContractError, match='missing'):
        CC.load(c, require_signed=False, plan_type=t)
