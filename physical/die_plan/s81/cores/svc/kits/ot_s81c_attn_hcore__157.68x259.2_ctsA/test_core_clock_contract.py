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
    monkeypatch.setattr(G,'core_tap_rows',lambda *_:[])
    out=tmp_path/'out';out.mkdir()
    G.core_latency_files(p,'tile',out,mean_contract=True)
    assert 'u_node clk 245.9 grid' in (out/'core_latency.txt').read_text()
    assert 'u_node clk 199.6 grid' in (out/'core_latency_ff.txt').read_text()
    r=json.loads((out/'core_latency.json').read_text())['rows'][0]
    assert r['signed'] and r['corners']['ff']['basis']=='pin_register_mean'
    assert 'signoff.json' in r['signoff_source']
    (tmp_path/'signoff.json').unlink()
    with pytest.raises(CC.ContractError,match='SIGNED'):G.core_latency_files(p,'tile',out,mean_contract=True)
