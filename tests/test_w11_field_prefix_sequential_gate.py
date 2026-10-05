import importlib.util
from pathlib import Path
import re
import pytest

PATH=Path(__file__).resolve().parents[1]/'tools/w11_field_prefix_sequential_gate.py'
spec=importlib.util.spec_from_file_location('field_gate',PATH)
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

def undo(source, prefix):
    return re.sub(r'\b'+prefix+r'(ot_\w+)\b',r'\1',source)

def test_exact_pins_and_candidate_body_only():
    sources=gate.pinned_sources()
    assert len(sources)==6
    ref=gate.generated(sources,'reference');sim=gate.generated(sources)
    for path,text in sources.items():
        assert undo(ref[path],'field_ref_')==text
        expected=gate.substitute(text) if path=='rtl/common/ot_prefix.sv' else text
        assert undo(sim[path],'field_sim_')==expected
    prefix=undo(sim['rtl/common/ot_prefix.sv'],'field_sim_')
    assert gate.ADD in prefix and gate.INC in prefix
    # Cross-file instances must follow definitions into the same namespace.
    assert 'field_sim_ot_v41_ksadd' in sim['rtl/v41rom/ot_v41_bmul2.sv']
    assert 'field_sim_ot_v41_csa' in sim['rtl/v41rom/ot_v41_bterm2_w10.sv']

def test_mutants_are_distinct_and_scoped():
    sources=gate.pinned_sources();normal=gate.generated(sources)
    carry=gate.generated(sources,'carry_mutant');reset=gate.generated(sources,'reset_mutant')
    assert [p for p in sources if normal[p]!=carry[p]]==['rtl/common/ot_prefix.sv']
    assert [p for p in sources if normal[p]!=reset[p]]==['rtl/v41rom/ot_v41_fadd.sv']
    for variant in ('increment_mutant','mul_sum_mutant'):
        mutant=gate.generated(sources,variant)
        assert [p for p in sources if normal[p]!=mutant[p]]==['rtl/common/ot_prefix.sv']
    with pytest.raises(ValueError):gate.generated(sources,'unknown')

def test_source_mismatch_fails_closed(monkeypatch):
    monkeypatch.setattr(gate,'SOURCES',{'rtl/common/ot_prefix.sv':'0'*64})
    with pytest.raises(ValueError,match='source pin mismatch'):gate.pinned_sources()
