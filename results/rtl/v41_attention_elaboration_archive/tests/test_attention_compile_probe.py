import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('probe', Path(__file__).parents[1]/'tools/v41_attention_compile_probe.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)

def test_full_shape_is_not_reduced_for_compile():
    assert P.PARAMS == dict(H=16,D=512,TD=32,NL=4,TROWS=640)
    assert P.PARAMS['NL'] * P.PARAMS['D']//P.PARAMS['TD'] == 64

def test_same_sources_and_parameters_flat_and_hierarchy(tmp_path):
    root = tmp_path/'source'
    flat = P.command(root, Path('/verilator'), tmp_path, None)
    vlt = tmp_path/'hier.vlt'
    hier = P.command(root, Path('/verilator'), tmp_path, vlt)
    idx = hier.index('--hierarchical')
    assert hier[:idx] + hier[idx+2:] == flat
    assert '--build' not in hier and '--exe' not in hier
    assert all(str(root/p) in flat for p in P.FILES)

def test_numeric_engine_is_present_no_stub():
    assert 'rtl/hdc/v41x/ot_hdc_v41x_attn.sv' in P.FILES
    assert not any('stub' in p for p in P.FILES)
