"""Independent admission truth-table and preserved-fixture mutation controls."""
import importlib.util
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('startup', ROOT / 'tools/w17_window_qdq8_connected_startup_prepare.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def admits(text, desc_count, acks, life_done_count, source_done_count, NOPS=6):
    block = text.split('  desc_v=0;\n', 1)[1].split('  for(integer p=', 1)[0]
    expressions = re.findall(r'(?:if|else if)\(([^\n]+?)\) begin', block)
    assert len(expressions) == 2
    state = dict(desc_count=desc_count, acks=acks, life_done_count=life_done_count,
                 source_done_count=source_done_count, NOPS=NOPS)
    return any(eval(e.replace('&&', ' and '), {'__builtins__': {}}, state) for e in expressions)


def test_startup_negative_and_original_mutant():
    old = (ROOT / m.OLD).read_text()
    new = (ROOT / m.NEW).read_text()
    for acks in range(32):
        assert not admits(new, 0, acks, 0, 0)
        assert admits(old, 0, acks, 0, 0)  # preserved failure, not accepted behavior
    assert admits(new, 0, 32, 0, 0)


def test_only_completed_previous_descriptor_continues():
    text = (ROOT / m.NEW).read_text()
    for nops in (6, 10):
        for count in range(1, nops):
            assert admits(text, count, 32, count, count, nops)
            assert not admits(text, count, 32, count-1, count, nops)
            assert not admits(text, count, 32, count, count-1, nops)
        assert not admits(text, nops, 32, nops, nops, nops)


def test_single_predicate_change_preserves_strict_assertion():
    old = (ROOT / m.OLD).read_text()
    new = (ROOT / m.NEW).read_text()
    assert new == old.replace(m.BEFORE, m.AFTER)
    assert old.split('  if(desc_accept)begin')[1] == new.split('  if(desc_accept)begin')[1]


def test_fresh_snapshot_copies_all_predictions(tmp_path):
    receipt = m.prepare(tmp_path / 'snapshot')
    assert receipt['changed_snapshot_files'] == ['model.json', 'sources/tb.sv']
    assert receipt['no_compile'] and receipt['no_runtime']
