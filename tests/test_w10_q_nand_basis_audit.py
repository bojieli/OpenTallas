import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('nand_basis',ROOT/'results/quality/w10_q_mask_basis_audit_20261001/reproduce.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_independent_OR_is_not_a_two_NAND_network():
    x=m.or_basis_witness()
    assert x['two_gate_implementations']==0
    assert x['three_gate_positive_truth_masks']==[3,5,14]

def test_negative_de_morgan_without_one_input_inversion_changes_truth():
    assert m.nand(3,10)!=14
    assert m.nand(3,5)==14
