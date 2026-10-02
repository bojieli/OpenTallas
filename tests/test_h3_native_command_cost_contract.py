import importlib.util
from pathlib import Path
import pytest

P = Path(__file__).resolve().parents[1] / 'tools/h3_native_command_cost_contract.py'
spec = importlib.util.spec_from_file_location('cost_contract', P)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

def test_exact_div_source_contract():
    d = C.generate()
    assert d['DIV']['divisor_binary32_hex'] == '45a00000'
    assert d['DIV']['implementation_owner'] is None
    assert not d['DIV']['native_GPU_binding']
    assert not d['DIV']['reciprocal_multiply_substitution_allowed']
    assert d['targets']['Qwen']['selected_PCs'] == 72
    assert d['targets']['DeepSeek']['selected_PCs'] == 80

def test_missing_cost_is_not_free():
    with pytest.raises(ValueError):
        C.compose([{'op': 'GATHER8'}], {})
    with pytest.raises(ValueError):
        C.compose([{'op': 'DIV'}], {'DIV': dict.fromkeys(C.COMPONENTS, 0)})

def test_serialized_cost_composition():
    costs = {'FADD': dict(zip(C.COMPONENTS, [1, 2, 3, 4, 5]))}
    assert C.compose([{'op': 'FADD'}, {'op': 'FADD'}], costs) == 30
    costs['FADD']['execute'] = None
    with pytest.raises(ValueError):
        C.compose([{'op': 'FADD'}], costs)

def test_unknown_bool_negative_and_extra_cost_rejected():
    for value in [True, -1, 1.5]:
        costs = {'AND': dict.fromkeys(C.COMPONENTS, 1)}
        costs['AND']['execute'] = value
        with pytest.raises(ValueError):
            C.compose([{'op': 'AND'}], costs)
    with pytest.raises(ValueError):
        C.compose([{'op': 'AND'}], {'AND': {**dict.fromkeys(C.COMPONENTS, 1), 'free_overlap': 0}})
