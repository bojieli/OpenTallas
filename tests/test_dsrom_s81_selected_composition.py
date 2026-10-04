import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('s81', ROOT/'tools/dsrom_s81_selected_composition.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def inputs():
    return [json.loads((ROOT/p).read_text()) for p in [s.BASE+'claude_S81.json', s.LEDGER,
        s.BASELINE, s.BASE+'W1_return_proxy.json', s.BASE+'projection_reservations.json']]


def test_selected_geometry_not_RD16_or_S82():
    d = s.build()
    assert (d['stages'],d['layer_dies'],d['total_dies'],d['pairs_per_rank_die'],d['BF_pairs'],d['q_pairs']) == (81,324,368,2417,519,1898)
    assert d['selected_return']['RD'] == 64
    assert not d['selected_return']['credit_RD16_adopted']


def test_exact_node_root_storage_once_and_prune_distinction():
    d = s.build(); r = d['selected_return']; o = d['return_options']
    assert r['total_state_bits'] == 5090*(2*64*65+66)+128*128*(65+66)
    assert r['nodes'] == 5090
    assert o['prune_only']['nodes'] == 5090
    assert o['prune_only']['retained_unary_nodes'] == 384
    assert o['contracted']['unary_stages_removed_vs_prune'] == 384
    assert o['prune_only']['screen_mm2'] > o['contracted']['screen_mm2']
    assert r['measured_latency_credit_cycles'] is None
    for o in o.values():
        assert not o['source_latency_or_fault_equivalence_qualified']
        assert o['root_logic_area_mm2'] is None
        assert not o['native_full_node_projection_is_incremental_debit']


def test_pruning_preserves_unary_ancestors_and_does_not_change_depth():
    groups=s.prune_inventory()
    assert sum(g['active_pairs'] for g in groups)==2417
    for g in groups:
        spans={(n['lo'],n['hi']) for n in g['nodes']}
        for leaf in range(2*g['active_pairs']):
            lo,hi=0,64
            for level in range(6):
                assert (lo,hi) in spans
                mid=(lo+hi)//2
                if leaf<mid:hi=mid
                else:lo=mid


def test_copies_remain_in_charged_field_and_no_fictional_area_fit():
    d=s.build()
    assert d['L4']['rank_copies']==4
    assert d['L4']['copied_elements']==130547712
    assert d['L4']['frame_credit_mm2']==0
    assert d['area']['contracted_Claude_screen_mm2']==pytest.approx(839.239,abs=.0005)
    assert d['area']['screen_mm2']==pytest.approx(841.6802584058435)
    assert d['area']['prune_only_debit_vs_contracted_mm2']==pytest.approx(2.44144502784)
    assert d['area']['screen_plus_excluded_adder_proxy_mm2']>d['area']['screen_mm2']
    assert d['area']['complete_area_mm2'] is None
    assert not d['area']['contextual_route_SS_FF_fit']


def test_source_price_and_wire_only_no_headline_adoption():
    d=s.build()
    a,b=d['scenarios']
    assert a['conditional_AR_tokens_s']==pytest.approx(2466.2,abs=.05)
    assert a['conditional_MTP_tokens_s']==pytest.approx(3742.8,abs=.05)
    assert b['conditional_AR_tokens_s']==pytest.approx(2574.1,abs=.05)
    assert d['stage_hops']['total']==80
    assert d['stage_hops']['added']==23
    assert d['stage_hops']['total_endpoint_wire_us']==pytest.approx(6)
    assert not d['adopted'] and d['headline_rate'] is None and not d['full_token_measured']


@pytest.mark.parametrize('kind',['RD16','pairs','copy_credit','copy_shape','wire'])
def test_source_contract_mutants_refused(kind):
    xs=copy.deepcopy(inputs())
    if kind=='RD16': xs[0]['priced']['S81_ragged_RD64_replicated']['return_option']='credit_RD16_ragged'
    if kind=='pairs': xs[0]['priced']['S81_ragged_RD64_replicated']['area']['pairs']=2388
    if kind=='copy_credit': xs[4]['records'][0]['reserved_frames_credit_mm2']=1
    if kind=='copy_shape': xs[4]['records'][0]['rank_slices'][1]['rows']=[0,64]
    if kind=='wire': xs[2]['baseline_at_model']['hop_us']-=.075
    with pytest.raises(ValueError):s.compose(*xs)


def test_fresh_replay_and_preserved_existing_model_calculations(tmp_path):
    expected=json.dumps(s.build(),indent=2,sort_keys=True)+'\n'
    assert (ROOT/s.OUT).read_text()==expected
    out=tmp_path/'out.json'
    subprocess.run(['python3',str(ROOT/'tools/uarch_model.py'),'--dsrom-selected-rom','--out',str(out)],check=True,stdout=subprocess.DEVNULL)
    assert out.read_text()==expected
    old=subprocess.check_output(['git','show','HEAD:tools/uarch_model.py'],cwd=ROOT,text=True)
    def functions(src):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(src).body
                if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    before,after=functions(old),functions((ROOT/'tools/uarch_model.py').read_text())
    for name,body in before.items():
        if name!='main': assert after[name]==body
