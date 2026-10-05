import ast,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_pc10_projection_r46 as m
from ds_hbm_pc10_composed_engine_r46 import require_PC9_origin,engine_class
from h3_ds_connected_provider_r37 import peer

@pytest.fixture(scope='module')
def inputs():return m.source_inputs()

@pytest.fixture(scope='module')
def plan():return peer('h4_c0_ds_tiled_continuation').GroupOperandTiles()


def dict_keywords(tree,function):
    f=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==function)
    return {k.arg for n in ast.walk(f) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict' for k in n.keywords}


def test_source_read_and_proof_record_keys_cover_pinned_sources(plan):
    D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002/inputs'
    tree=ast.parse((D/'h4_c0_ds_source_views.py').read_bytes())
    f=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_read_words')
    receipt_node=next(n.value for n in ast.walk(f) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='receipt' for t in n.targets))
    tile=plan.tile(10,95,7,896);r,p=m.source_receipt_schema(plan,95,tile['source_spans'][-1],Path('/tmp/result/events.sqlite'))
    assert {k.arg for k in receipt_node.keywords}==set(r)
    raw=peer('h4_c0_ds_tiled_continuation').pinned('tools/h3_complete_native_calendar.py','b2120f45d9a9fc419bc78d52d3224065483e4c87')
    f=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='verify_ds_operand_journal')
    ret=next(n.value for n in ast.walk(f) if isinstance(n,ast.Return))
    assert {k.arg for k in ret.keywords}<=set(p)
    assert p['source_reference']['code_index']==15 and r['source_words']==128


def test_call_record_covers_original_calendar_return_updates_and_wrapper(plan,inputs):
    n,h,manifest=inputs
    r,bridge=m.call_schema(plan,h,95,Path('/tmp/events.sqlite'));r=r['record']
    tree=ast.parse((ROOT/'tools/h3_complete_native_calendar.py').read_bytes())
    f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute_ds_group128_tiles')
    ret=next(n.value for n in ast.walk(f) if isinstance(n,ast.Return))
    assert {k.arg for k in ret.keywords}<=r.keys()
    f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute_ds_provider_group128')
    update=next(n for n in ast.walk(f) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='result' and n.func.attr=='update')
    assert {k.arg for k in update.keywords}<=r.keys()
    assert len(r['actual_source_receipts'])==512 and len(r['output_span_receipts'])==64
    assert r['publication'] is r['actual_publication'] and r['actual_RF_mirror_journal'] is r['actual_result_journal']
    assert bridge>0 and len(m.canonical(r))>1000000


def test_full_projection_components_and_source_addressed_refinement(inputs):
    r=m.project(*inputs)
    assert sum(r['components'].values())==r['journal_capacity_bytes']>912931843936
    assert sum(r['source_addressed_components'].values())==r['source_addressed_candidate_projection_bytes']
    assert r['source_addressed_candidate_projection_bytes']>616176447328
    assert r['prefix_metadata']['source_read_receipt_records']==51456
    assert r['prefix_metadata']['numeric_call_records']==928
    assert r['PC10_RF_sector_address_derivation']['total']==1081344
    assert r['expected_output_comparisons']==1664 and r['source_read_receipts']==49152
    assert r['finite_sector_tick_upper']<r['integer_schema_upper']
    assert not r['runtime_GO'] and r['physical_critical_path_edges'] is None


def test_RF_home_mutation_refuses_refinement(plan,inputs):
    import copy
    n,h,manifest=inputs;h=copy.deepcopy(h)
    i=next(i for i,x in enumerate(h) if x['version']=='DeepSeek.9.zpart.67')
    h[i]['word_count']=128
    with pytest.raises(ValueError):m.exact_PC10_RF_requests(plan,h)


def origin():
    version='DeepSeek.9.zpart.67';dest='DeepSeek.10.z.68'
    witness=SimpleNamespace(failed=False,seen={(9,version,r,1,'data') for r in range(64)},expected={(10,dest,r,1,'data'):{} for r in range(96)})
    return SimpleNamespace(retired=set(range(10)),generation=1,provider=SimpleNamespace(witness=witness),
        native={'instructions':[{}]*9+[dict(rank_bindings=[dict(rank=r) for r in range(64)],writes=[dict(version=version)])]},
        groups=SimpleNamespace(endpoint=SimpleNamespace(identity=lambda r:dict(version=dest))))


def test_origin_metadata_gate_admits_complete_scope_without_executing():require_PC9_origin(origin())

@pytest.mark.parametrize('missing',['retirement','producer','observer','failed'])
def test_origin_refusal_before_PC10_provider_call(missing):
    e=origin()
    if missing=='retirement':e.retired.remove(9)
    if missing=='producer':e.provider.witness.seen.remove((9,'DeepSeek.9.zpart.67',63,1,'data'))
    if missing=='observer':e.provider.witness.expected.pop((10,'DeepSeek.10.z.68',95,1,'data'))
    if missing=='failed':e.provider.witness.failed=True
    with pytest.raises(ValueError):require_PC9_origin(e)


def test_default_off_and_physical_backend_refusal():
    class Prefix:pass
    assert engine_class(Prefix).__name__=='Engine'
    with pytest.raises(ValueError,match='port-bound'):engine_class(Prefix,finite_pc10=True,physical_backend=True)


def test_prepared_runner_composes_exact_source_before_any_execution():
    tree=ast.parse((ROOT/'tools/ds_hbm_source_prefix_r46.py').read_text())
    imports={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    assert {'ds_hbm_source_prefix_r45','ds_hbm_pc10_engine_r44','ds_hbm_pc10_composed_engine_r46','ds_hbm_pc10_projection_r46'}<=imports
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    text=ast.unparse(main)
    assert text.index('explicit default-off')<text.index('args.out.mkdir()')
    assert 'finite_pc10=args.finite_pc10' in text and 'retire_unconsumed=args.retire_unconsumed' in text
    assert text.index('engine =')<text.index('if args.preflight_only:')<text.index('engine.run(')
    assert 'output_root=args.out' in text and 'free < priced[\'journal_capacity_bytes\']' in text
    assert not any(s in text for s in ('sched_setaffinity','RLIMIT_AS','RLIMIT_CPU','RLIMIT_FSIZE'))
